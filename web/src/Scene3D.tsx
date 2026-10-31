import { useEffect, useRef } from 'react';
import * as THREE from 'three';

// Illustrative scene: the node sits at the origin facing -Z. A generic figure is placed from the
// radar's range and the camera's bearing estimate; neither is a calibrated position.
export type ScenePerson = { state: 'present' | 'last_seen' | 'none'; distanceM: number; bearingDeg: number };
export type SceneView = 'perspective' | 'overhead';

const MAX_RANGE = 6, HALF_FOV = Math.PI / 3, CAMERA_HALF_FOV = THREE.MathUtils.degToRad(25);
const VIEWS: Record<SceneView, { position: THREE.Vector3; look: THREE.Vector3 }> = {
  perspective: { position: new THREE.Vector3(0, 4.6, 4.4), look: new THREE.Vector3(0, 0.3, -2.9) },
  overhead: { position: new THREE.Vector3(0, 11.5, -2.85), look: new THREE.Vector3(0, 0, -2.9) },
};
const HUMAN = new THREE.Color('#10b981'), GHOST = new THREE.Color('#94a3b8');

function flatArc(inner: number, outer: number, color: string, opacity: number) {
  const geometry = new THREE.RingGeometry(inner, outer, 64, 1, Math.PI / 2 - HALF_FOV, 2 * HALF_FOV);
  geometry.rotateX(-Math.PI / 2);
  return new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false }));
}

export function Scene3D({ person, view }: { person: ScenePerson; view: SceneView }) {
  const host = useRef<HTMLDivElement>(null);
  const latest = useRef({ person, view });
  latest.current = { person, view };

  useEffect(() => {
    const element = host.current!;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    element.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    camera.position.copy(VIEWS.perspective.position);
    const look = VIEWS.perspective.look.clone();

    scene.add(new THREE.HemisphereLight(0xffffff, 0xe2e8f0, 2.4));
    const sun = new THREE.DirectionalLight(0xffffff, 1.4);
    sun.position.set(3, 8, 4);
    scene.add(sun);

    // Floor: radar fan with 1 m rings, and the camera's assumed field of view.
    const fan = new THREE.Mesh(
      (() => { const g = new THREE.CircleGeometry(MAX_RANGE, 64, Math.PI / 2 - HALF_FOV, 2 * HALF_FOV); g.rotateX(-Math.PI / 2); return g; })(),
      new THREE.MeshBasicMaterial({ color: '#0ea5e9', transparent: true, opacity: 0.05, depthWrite: false }));
    scene.add(fan);
    for (let metre = 1; metre <= MAX_RANGE; metre++) scene.add(flatArc(metre - 0.012, metre + 0.012, '#94a3b8', 0.45));
    const cameraEdges = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0.01, 0), new THREE.Vector3(-Math.sin(CAMERA_HALF_FOV) * MAX_RANGE, 0.01, -Math.cos(CAMERA_HALF_FOV) * MAX_RANGE),
      new THREE.Vector3(0, 0.01, 0), new THREE.Vector3(Math.sin(CAMERA_HALF_FOV) * MAX_RANGE, 0.01, -Math.cos(CAMERA_HALF_FOV) * MAX_RANGE)]);
    scene.add(new THREE.LineSegments(cameraEdges, new THREE.LineBasicMaterial({ color: '#10b981', transparent: true, opacity: 0.5 })));

    // Node: a small box with a lens.
    const node = new THREE.Group();
    const body = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.22, 0.2), new THREE.MeshStandardMaterial({ color: '#334155', roughness: 0.5 }));
    body.position.y = 0.11;
    const lens = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.05, 24), new THREE.MeshStandardMaterial({ color: '#0ea5e9' }));
    lens.rotation.x = Math.PI / 2;
    lens.position.set(0, 0.12, -0.11);
    node.add(body, lens);
    scene.add(node);

    // Generic figure built from simple shapes; not a reconstruction of the real person.
    const material = new THREE.MeshStandardMaterial({ color: HUMAN, roughness: 0.55, transparent: true, opacity: 0 });
    const figure = new THREE.Group();
    const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.2, 0.75, 8, 20), material);
    torso.position.y = 0.72;
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.15, 24, 16), material);
    head.position.y = 1.38;
    const shadow = new THREE.Mesh(new THREE.CircleGeometry(0.34, 32).rotateX(-Math.PI / 2),
      new THREE.MeshBasicMaterial({ color: '#0f172a', transparent: true, opacity: 0, depthWrite: false }));
    shadow.position.y = 0.005;
    const halo = new THREE.Mesh(new THREE.RingGeometry(0.4, 0.46, 48).rotateX(-Math.PI / 2),
      new THREE.MeshBasicMaterial({ color: '#10b981', transparent: true, opacity: 0, depthWrite: false }));
    halo.position.y = 0.01;
    figure.add(torso, head, shadow, halo);
    figure.position.set(0, 0, -2.5);
    scene.add(figure);

    const resize = () => {
      const { clientWidth: width, clientHeight: height } = element;
      renderer.setSize(width, height, false);
      camera.aspect = width / Math.max(height, 1);
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    resize();

    const goal = new THREE.Vector3();
    let frame = 0;
    const clock = new THREE.Clock();
    const tick = () => {
      frame = requestAnimationFrame(tick);
      const t = clock.getElapsedTime();
      const { person: target, view: targetView } = latest.current;
      const smoothing = reduceMotion ? 1 : 0.08;

      const bearing = THREE.MathUtils.degToRad(target.bearingDeg);
      goal.set(Math.sin(bearing) * target.distanceM, 0, -Math.cos(bearing) * target.distanceM);
      if (target.state !== 'none') figure.position.lerp(goal, smoothing);
      const opacity = target.state === 'present' ? 1 : target.state === 'last_seen' ? 0.35 : 0;
      material.opacity += (opacity - material.opacity) * smoothing;
      material.color.lerp(target.state === 'present' ? HUMAN : GHOST, smoothing);
      (shadow.material as THREE.MeshBasicMaterial).opacity = material.opacity * 0.12;
      const haloMaterial = halo.material as THREE.MeshBasicMaterial;
      const pulse = reduceMotion ? 0.5 : (t * 0.8) % 1;
      halo.scale.setScalar(target.state === 'present' ? 1 + pulse * 1.4 : 1);
      haloMaterial.opacity = target.state === 'present' ? (1 - pulse) * 0.6 : 0;
      figure.visible = material.opacity > 0.01;
      if (!reduceMotion && target.state === 'present') torso.position.y = head.position.y - 0.66 + Math.sin(t * 2.2) * 0.012;

      camera.position.lerp(VIEWS[targetView].position, reduceMotion ? 1 : 0.06);
      look.lerp(VIEWS[targetView].look, reduceMotion ? 1 : 0.06);
      camera.lookAt(look);
      renderer.render(scene, camera);
    };
    tick();

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      scene.traverse(object => {
        if (object instanceof THREE.Mesh || object instanceof THREE.LineSegments) {
          object.geometry.dispose();
          (Array.isArray(object.material) ? object.material : [object.material]).forEach(item => item.dispose());
        }
      });
      renderer.dispose();
      element.removeChild(renderer.domElement);
    };
  }, []);

  return <div ref={host} className="scene3d" role="img"
    aria-label={person.state === 'none' ? 'Illustrative scene, no person shown'
      : `Illustrative figure about ${person.distanceM.toFixed(1)} m ahead${person.state === 'last_seen' ? ', last seen' : ''}`} />;
}
