import * as THREE from 'three'

/** A same-device port connection needs two control points to form a real loop. */
export function linkCurve(start: THREE.Vector3, end: THREE.Vector3, index: number, self: boolean): THREE.Curve<THREE.Vector3> {
  if (self) {
    const reach = 6 + index * 2
    return new THREE.CubicBezierCurve3(start,
      start.clone().add(new THREE.Vector3(-reach, reach, reach)),
      start.clone().add(new THREE.Vector3(reach, reach, reach)), end)
  }
  const middle = start.clone().lerp(end, .5)
  middle.z += 3 + index * 2; middle.y += 3 + index
  return new THREE.QuadraticBezierCurve3(start, middle, end)
}

/** Fit nodes, tier titles AND all curved links, even on narrow canvases. */
export function fittedView(box: THREE.Box3, fov: number, aspect: number, top = false) {
  const center = box.getCenter(new THREE.Vector3())
  const radius = box.getSize(new THREE.Vector3()).length() / 2
  const vertical = THREE.MathUtils.degToRad(fov / 2)
  const halfFov = Math.min(vertical, Math.atan(Math.tan(vertical) * Math.max(aspect, .01)))
  const distance = Math.max(8, radius / Math.sin(halfFov) * 1.12)
  const direction = top ? new THREE.Vector3(0, 1, .01) : new THREE.Vector3(.85, .65, 1)
  return { center, position: center.clone().add(direction.normalize().multiplyScalar(distance)), distance }
}
