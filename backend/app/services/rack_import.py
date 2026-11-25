"""机柜 Excel 模板和逐行导入；不创建模拟业务数据。"""
import io
from decimal import Decimal, InvalidOperation
from zipfile import ZipFile

from fastapi import HTTPException, UploadFile
from fastapi.responses import Response
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy.exc import IntegrityError

from app.models.models import Area, DataCenter
from app.schemas.common import RackCreate, RackImportResult, RackImportError
from app.services.rack import create_rack_record

COLUMNS = [
    ("data_center_id", "机房ID"), ("area_id", "区域ID"), ("code", "机柜编号"),
    ("row_position", "行"), ("column_position", "列"), ("orientation", "朝向"),
    ("total_u", "总U数"), ("is_active", "状态"), ("remark", "备注"),
]
ALIASES = {key: key for key, _ in COLUMNS}
ALIASES.update({label: key for key, label in COLUMNS})
MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 1000
ORIENTATIONS = {"北向": "north", "南向": "south", "东向": "east", "西向": "west"}


def template_response(db):
    wb = Workbook()
    ws = wb.active
    ws.title = "机柜导入模板"
    ws.append([label for _, label in COLUMNS])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = "A1:I1"
    # Keep the data sheet empty, but make future rack codes text (e.g. 001).
    for index, cell in enumerate(ws[1], 1):
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="244768")
        ws.column_dimensions[get_column_letter(index)].width = 20 if index < 9 else 40
    ws.column_dimensions["C"].number_format = "@"
    ws.row_dimensions[1].height = 28
    for col, choices in [("F", '"北向,南向,东向,西向"'), ("H", '"启用,停用"')]:
        validation = DataValidation(type="list", formula1=choices, allow_blank=True)
        validation.errorTitle = "填写错误"
        validation.error = "请选择下拉列表中的值"
        validation.showErrorMessage = True
        ws.add_data_validation(validation)
        validation.add(f"{col}2:{col}{MAX_ROWS + 1}")
    for col in ("A", "B", "D", "E", "G"):
        validation = DataValidation(type="whole", operator="between", formula1=1, formula2=2147483647,
                                    allow_blank=col not in ("A", "B"))
        validation.showErrorMessage = True
        validation.error = "请填写大于零的整数"
        ws.add_data_validation(validation)
        validation.add(f"{col}2:{col}{MAX_ROWS + 1}")

    help_sheet = wb.create_sheet("填写说明")
    for line in [
        "请在【机柜导入模板】中从第2行开始填写；不要删除表头。此模板没有模拟机柜数据。",
        "必填：机房ID、区域ID、机柜编号。机房和区域必须已存在且已启用，区域必须属于指定机房。",
        "请从【机房区域参考】查找数字ID，不要填写机房名称或区域名称；参考内容是下载时的快照。",
        "机柜编号填写末尾部分，如001；系统自动生成机房ID_区域ID_001，同一区域内不能重复。001等请按文本填写。",
        "也可填写带当前机房和区域前缀的完整编号，不会重复添加前缀；完整编号最多50个字符。",
        "行、列：填写正整数，留空默认1；总U数：填写正整数，留空默认42。",
        "朝向：北向/南向/东向/西向，或 north/south/east/west；留空默认北向。",
        "状态：启用/停用，或 true/false、1/0；留空默认启用。备注可留空。",
        "不用填写平面坐标，系统按 X=(列-1)×2.2、Y=(行-1)×4.0 自动计算。",
        "支持中文标准表头及对应英文字段名；不支持公式，请填写实际值。旧版.xls请另存为.xlsx。",
        "每次最多1000条、5MB。只新增、不覆盖：逐行保存成功记录，失败记录会显示Excel行号和原因。",
        "失败后只重新导入修正后的失败行，避免重复导入已成功记录。空行会自动跳过。",
    ]:
        help_sheet.append([line])
    help_sheet.column_dimensions["A"].width = 100
    for row in help_sheet:
        row[0].alignment = Alignment(wrap_text=True, vertical="center")
        help_sheet.row_dimensions[row[0].row].height = 40

    reference = wb.create_sheet("机房区域参考")
    reference.append(["机房ID", "机房名称", "区域ID", "区域名称", "机房状态", "区域状态"])
    for dc, area in db.query(DataCenter, Area).outerjoin(Area, Area.data_center_id == DataCenter.id).order_by(DataCenter.id, Area.id):
        reference.append([dc.id, dc.name, area.id if area else None, area.name if area else "（暂无区域）",
                          "启用" if dc.is_active else "停用", ("启用" if area.is_active else "停用") if area else "-"])
    for row in reference:
        for cell in row:
            if isinstance(cell.value, str):
                cell.data_type = "s"
    reference.freeze_panes = "A2"
    for index, cell in enumerate(reference[1], 1):
        cell.font = Font(bold=True)
        reference.column_dimensions[get_column_letter(index)].width = 26
    output = io.BytesIO()
    wb.save(output)
    wb.close()
    return Response(output.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=racks_template.xlsx"})


def _blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def parse_rack_upload(file: UploadFile):
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="仅支持.xlsx文件，请下载标准模板填写")
    content = file.file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="文件不能超过5MB")
    wb = None
    try:
        with ZipFile(io.BytesIO(content)) as archive:
            if sum(item.file_size for item in archive.infolist()) > 50 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Excel解压后内容过大，请拆分后导入")
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=False, keep_links=False)
        ws = wb["机柜导入模板"] if "机柜导入模板" in wb.sheetnames else wb.worksheets[0]
        if (ws.max_row or 0) > MAX_ROWS + 1 or (ws.max_column or 0) > len(COLUMNS):
            raise HTTPException(status_code=400, detail="表格最多1000行数据、9列，请按标准模板填写")
        rows = ws.iter_rows()
        header = next(rows, ())
        fields = []
        for cell in header:
            label = str(cell.value).strip() if not _blank(cell.value) else ""
            field = ALIASES.get(label)
            if not field or field in fields:
                raise HTTPException(status_code=400, detail="表头缺失、重复或无法识别，请使用标准模板")
            fields.append(field)
        if not {"data_center_id", "area_id", "code"}.issubset(fields):
            raise HTTPException(status_code=400, detail="缺少必填表头：机房ID、区域ID、机柜编号")
        records = []
        for number, cells in enumerate(rows, 2):
            if number > MAX_ROWS + 1:
                raise HTTPException(status_code=400, detail="每次最多导入1000条")
            if all(_blank(cell.value) for cell in cells):
                continue
            formula = any(cell.data_type == "f" for cell in cells)
            records.append((number, dict(zip(fields, [cell.value for cell in cells])), formula))
        if not records:
            raise HTTPException(status_code=400, detail="模板没有机柜数据，请从第2行开始填写")
        return records
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail="无法读取Excel，请检查文件是否损坏或加密") from exc
    finally:
        if wb:
            wb.close()


def _positive_int(value, label, default=None):
    if _blank(value):
        if default is not None:
            return default
        raise ValueError(f"{label}不能为空")
    try:
        if isinstance(value, bool):
            raise ValueError()
        number = Decimal(str(value).strip())
        if not number.is_finite() or number != number.to_integral_value() or not 1 <= number <= 2147483647:
            raise ValueError()
        return int(number)
    except (ValueError, InvalidOperation):
        raise ValueError(f"{label}必须是大于零的整数")


def normalize_rack_row(row):
    code = "" if _blank(row.get("code")) else str(row["code"]).strip()
    if not code or len(code) > 50:
        raise ValueError("机柜编号必填且不能超过50个字符")
    orientation = "north" if _blank(row.get("orientation")) else str(row["orientation"]).strip().lower()
    orientation = ORIENTATIONS.get(orientation, orientation)
    if orientation not in ("north", "south", "east", "west"):
        raise ValueError("朝向只能填写北向、南向、东向、西向或对应英文代码")
    status = "启用" if _blank(row.get("is_active")) else str(row["is_active"]).strip().lower()
    if status not in ("启用", "停用", "true", "false", "1", "0"):
        raise ValueError("状态只能填写启用/停用、true/false或1/0")
    return RackCreate(
        data_center_id=_positive_int(row.get("data_center_id"), "机房ID"),
        area_id=_positive_int(row.get("area_id"), "区域ID"), code=code,
        row_position=_positive_int(row.get("row_position"), "行", 1),
        column_position=_positive_int(row.get("column_position"), "列", 1),
        total_u=_positive_int(row.get("total_u"), "总U数", 42),
        orientation=orientation, is_active=status in ("启用", "true", "1"),
        remark=None if _blank(row.get("remark")) else str(row["remark"]).strip(),
    )


def import_racks(db, records, user):
    errors = []
    imported = 0
    for number, row, formula in records:
        try:
            if formula:
                raise ValueError("不支持公式，请填写实际值")
            create_rack_record(db, normalize_rack_row(row), user)
            imported += 1
        except (ValueError, HTTPException, IntegrityError) as exc:
            db.rollback()
            reason = "机柜编号重复或关联数据已变更，请检查后重试" if isinstance(exc, IntegrityError) else str(getattr(exc, "detail", exc))
            errors.append(RackImportError(row=number, message=reason))
    return RackImportResult(total=len(records), imported=imported, failed=len(errors), errors=errors,
                            message=f"导入完成：成功 {imported} 条，失败 {len(errors)} 条")
