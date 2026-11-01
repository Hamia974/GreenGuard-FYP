import * as THREE from "three";

export interface NetworkSceneOptions {
  canvas: HTMLCanvasElement;
  container: HTMLElement;
  /** Receives the smoothed pointer position (-1 to 1) on every frame. */
  onPointerFrame?: (x: number, y: number) => void;
  animate: boolean;
  /** Which side of the screen holds most nodes: 1 for right, -1 for left. */
  networkSide: 1 | -1;
}

const NODE_COUNT = 48;
const PHONE_NODE_COUNT = 22;
const PHONE_MAX_ASPECT = 1;
/** Node diameter and link reach, in CSS pixels. */
const NODE_SIZE_PX = 17;
const MAX_LINK_PX = 125;
const MAX_LINK_OPACITY = 0.55;
/** Nodes sit on the field: this far down the screen, just below the horizon. */
const GRASS_TOP = 0.3;
/** How far a node sways on the spot, in CSS pixels. */
const SWAY_PX = 3;
/** Candidate spots tried per node; more gives a more even spread. */
const SPOT_CANDIDATES = 14;
/** Nodes form one band across the screen, ending above the text. */
const TEXT_BLOCK_TOP = 0.46;
const PHONE_TEXT_TOP = 0.55;
const ROW_SPACING = 5.2;
const FIELD_OF_VIEW = 50;
const CAMERA_Z = 20;
const STILL_FRAME_MS = 4000;

interface FieldNode {
  /** Distance across the screen from the text's side, 0 to 1. */
  across: number;
  /** Distance down the screen, 0 to 1. */
  down: number;
  swayPhase: number;
}

/** Small seeded generator, so the nodes start the same way on every visit. */
function createRandom(initialSeed: number) {
  let seed = initialSeed;
  return () => {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  };
}

/** A crisp node: a solid dot inside a thin ring, with no soft glow. */
function createNodeTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 128;
  const context = canvas.getContext("2d");
  if (context) {
    context.strokeStyle = "#fff4dc";
    context.lineWidth = 7;
    context.beginPath();
    context.arc(64, 64, 52, 0, Math.PI * 2);
    context.stroke();
    context.fillStyle = "#fff4dc";
    context.beginPath();
    context.arc(64, 64, 22, 0, Math.PI * 2);
    context.fill();
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

/** Spreads nodes in one band across the field, between the horizon and the text. */
function buildNodes(count: number, isPhone: boolean): FieldNode[] {
  const random = createRandom(4242);
  const nodes: FieldNode[] = [];

  const pickOpenSpot = () => {
    const across = random();
    const lowest = isPhone ? PHONE_TEXT_TOP : TEXT_BLOCK_TOP;
    return { across, down: GRASS_TOP + random() * (lowest - GRASS_TOP) };
  };
  const gapToNearest = (spot: { across: number; down: number }) =>
    nodes.reduce(
      (nearest, node) => Math.min(nearest, Math.hypot(node.across - spot.across, node.down - spot.down)),
      Infinity
    );

  for (let index = 0; index < count; index++) {
    let best = pickOpenSpot();
    for (let attempt = 1; attempt < SPOT_CANDIDATES; attempt++) {
      const candidate = pickOpenSpot();
      if (gapToNearest(candidate) > gapToNearest(best)) best = candidate;
    }
    nodes.push({ ...best, swayPhase: random() * Math.PI * 2 });
  }
  return nodes;
}

/**
 * Decorative 3D layer for the landing hero: small nodes resting on the field, a crop-row
 * grid and a scan line drawn over the video. It does not represent sensors or
 * real analysis. Returns a cleanup function that releases every WebGL resource.
 */
export function startNetworkScene({
  canvas,
  container,
  onPointerFrame,
  animate,
  networkSide,
}: NetworkSceneOptions) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setClearColor(0x000000, 0);
  renderer.autoClear = false;
  renderer.setPixelRatio(Math.min(1.75, window.devicePixelRatio || 1));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(FIELD_OF_VIEW, 2, 0.1, 420);

  // Nodes are drawn in screen pixels on top of the 3D scene, so they stay small and crisp.
  const overlay = new THREE.Scene();
  const overlayCamera = new THREE.OrthographicCamera(0, 1, 0, 1, -1, 1);

  const isPhone = container.clientWidth / Math.max(container.clientHeight, 1) < PHONE_MAX_ASPECT;
  const nodes = buildNodes(isPhone ? PHONE_NODE_COUNT : NODE_COUNT, isPhone);
  const nodeCount = nodes.length;

  const nodePositions = new Float32Array(nodeCount * 3);
  const nodeAlphas = new Float32Array(nodeCount);
  const nodeColors = new Float32Array(nodeCount * 4).fill(1);
  const nodeGeometry = new THREE.BufferGeometry();
  nodeGeometry.setAttribute("position", new THREE.BufferAttribute(nodePositions, 3));
  nodeGeometry.setAttribute("color", new THREE.BufferAttribute(nodeColors, 4));
  const nodeTexture = createNodeTexture();
  const nodeMaterial = new THREE.PointsMaterial({
    map: nodeTexture,
    size: NODE_SIZE_PX,
    sizeAttenuation: false,
    vertexColors: true,
    transparent: true,
    depthTest: false,
    depthWrite: false,
  });
  const nodePoints = new THREE.Points(nodeGeometry, nodeMaterial);
  nodePoints.frustumCulled = false;

  // Room for every possible pair; only pairs close enough are drawn each frame.
  const maxLinkPairs = (nodeCount * (nodeCount - 1)) / 2;
  const linkPositions = new Float32Array(maxLinkPairs * 6);
  const linkColors = new Float32Array(maxLinkPairs * 8);
  const linkGeometry = new THREE.BufferGeometry();
  linkGeometry.setAttribute("position", new THREE.BufferAttribute(linkPositions, 3));
  linkGeometry.setAttribute("color", new THREE.BufferAttribute(linkColors, 4));
  const linkMaterial = new THREE.LineBasicMaterial({
    vertexColors: true,
    transparent: true,
    depthTest: false,
    depthWrite: false,
  });
  const links = new THREE.LineSegments(linkGeometry, linkMaterial);
  links.frustumCulled = false;
  overlay.add(links);
  overlay.add(nodePoints);

  let screenWidth = 1;
  let screenHeight = 1;

  const updateNodes = (seconds: number, parallaxX: number, parallaxY: number) => {
    nodes.forEach((node, index) => {
      const offset = index * 3;
      const fromLeft = networkSide === 1 ? node.across : 1 - node.across;
      nodePositions[offset] =
        fromLeft * screenWidth + Math.sin(seconds * 0.5 + node.swayPhase) * SWAY_PX + parallaxX * -14;
      nodePositions[offset + 1] =
        node.down * screenHeight + Math.cos(seconds * 0.4 + node.swayPhase) * SWAY_PX + parallaxY * -10;
      // Each node breathes gently where it sits.
      nodeAlphas[index] = 0.72 + 0.28 * Math.sin(seconds * 0.8 + node.swayPhase);
      nodeColors[index * 4 + 3] = nodeAlphas[index];
    });
    nodeGeometry.attributes.position.needsUpdate = true;
    nodeGeometry.attributes.color.needsUpdate = true;

    let linkVertex = 0;
    for (let a = 0; a < nodeCount; a++) {
      for (let b = a + 1; b < nodeCount; b++) {
        const dx = nodePositions[a * 3] - nodePositions[b * 3];
        const dy = nodePositions[a * 3 + 1] - nodePositions[b * 3 + 1];
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance >= MAX_LINK_PX) continue;

        const opacity =
          (1 - distance / MAX_LINK_PX) * MAX_LINK_OPACITY * Math.min(nodeAlphas[a], nodeAlphas[b]);
        [a, b].forEach((nodeIndex) => {
          linkPositions.set(nodePositions.subarray(nodeIndex * 3, nodeIndex * 3 + 3), linkVertex * 3);
          linkColors.set([1, 0.96, 0.86, opacity], linkVertex * 4);
          linkVertex++;
        });
      }
    }
    linkGeometry.setDrawRange(0, linkVertex);
    linkGeometry.attributes.position.needsUpdate = true;
    linkGeometry.attributes.color.needsUpdate = true;
  };

  const rowPositions: number[] = [];
  const rowColors: number[] = [];
  for (let index = -14; index <= 14; index++) {
    const x = index * ROW_SPACING;
    rowPositions.push(x, 0, 16, x, 0, -160);
    rowColors.push(1, 0.82, 0.55, 0, 0, 0);
  }
  const rowGeometry = new THREE.BufferGeometry();
  rowGeometry.setAttribute("position", new THREE.Float32BufferAttribute(rowPositions, 3));
  rowGeometry.setAttribute("color", new THREE.Float32BufferAttribute(rowColors, 3));
  const rowMaterial = new THREE.LineBasicMaterial({
    vertexColors: true,
    transparent: true,
    opacity: 0.34,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const rows = new THREE.LineSegments(rowGeometry, rowMaterial);
  scene.add(rows);

  const sweepGeometry = new THREE.PlaneGeometry(150, 1.2);
  const sweepMaterial = new THREE.MeshBasicMaterial({
    color: 0xffe2b0,
    transparent: true,
    opacity: 0.42,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  const sweep = new THREE.Mesh(sweepGeometry, sweepMaterial);
  sweep.rotation.x = -Math.PI / 2;
  sweep.position.y = 0.05;
  scene.add(sweep);

  let targetX = 0;
  let targetY = 0;
  let pointerX = 0;
  let pointerY = 0;
  let lastTime = 0;

  const render = (time: number) => {
    lastTime = time;
    const seconds = time / 1000;
    pointerX += (targetX - pointerX) * 0.05;
    pointerY += (targetY - pointerY) * 0.05;

    // Tilted down so the 3D horizon lines up with the video's horizon.
    const height = 10.5 - pointerY * 0.9;
    camera.position.set(pointerX * 2.6, height, CAMERA_Z);
    camera.lookAt(pointerX * -1.5, height - 22.4, -71);

    sweep.position.z = 16 - ((seconds * 17) % 160);
    sweepMaterial.opacity = 0.42 * (1 - Math.abs(sweep.position.z + 64) / 90);
    rows.position.z = (seconds * 2.4) % ROW_SPACING;
    updateNodes(seconds, pointerX, pointerY);

    onPointerFrame?.(pointerX, pointerY);
    renderer.clear();
    renderer.render(scene, camera);
    renderer.render(overlay, overlayCamera);
  };

  const resize = () => {
    const { clientWidth: width, clientHeight: height } = container;
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    screenWidth = width;
    screenHeight = height;
    overlayCamera.right = width;
    overlayCamera.bottom = height;
    overlayCamera.updateProjectionMatrix();
    render(lastTime || STILL_FRAME_MS);
  };
  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(container);
  resize();

  const handlePointerMove = (event: PointerEvent) => {
    const bounds = container.getBoundingClientRect();
    targetX = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
    targetY = ((event.clientY - bounds.top) / bounds.height) * 2 - 1;
  };
  const handlePointerLeave = () => {
    targetX = 0;
    targetY = 0;
  };

  let frame = 0;
  if (animate) {
    window.addEventListener("pointermove", handlePointerMove, { passive: true });
    document.documentElement.addEventListener("pointerleave", handlePointerLeave);
    const loop = (time: number) => {
      frame = requestAnimationFrame(loop);
      if (!document.hidden) render(time);
    };
    frame = requestAnimationFrame(loop);
  } else {
    render(STILL_FRAME_MS);
  }

  return () => {
    cancelAnimationFrame(frame);
    resizeObserver.disconnect();
    window.removeEventListener("pointermove", handlePointerMove);
    document.documentElement.removeEventListener("pointerleave", handlePointerLeave);
    nodeGeometry.dispose();
    nodeMaterial.dispose();
    nodeTexture.dispose();
    linkGeometry.dispose();
    linkMaterial.dispose();
    rowGeometry.dispose();
    rowMaterial.dispose();
    sweepGeometry.dispose();
    sweepMaterial.dispose();
    renderer.dispose();
  };
}
