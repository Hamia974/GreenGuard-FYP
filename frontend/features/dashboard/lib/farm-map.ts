/**
 * Canvas renderer for the dashboard's farm map. Farm positions come from each
 * farm's saved latitude and longitude; the contours and rivers are decorative
 * and do not show real geography. Motion (pulses, radar sweep, river flow) is
 * frontend animation only. Every farm is labelled, the chosen one first; a
 * label that would overlap one already placed is skipped until the pointer is
 * over its farm.
 */

export type FarmMapStatus = "healthy" | "watch" | "risk" | "critical" | "unknown";

export interface FarmMapFarm {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  status: FarmMapStatus;
}

/** The part of the canvas, in CSS pixels, that is not covered by panels. */
export interface FarmMapArea {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface FarmMapState {
  farms: FarmMapFarm[];
  selectedId: string | null;
  rtl: boolean;
}

interface FarmMapOptions {
  getArea: (width: number, height: number) => FarmMapArea;
  onSelect: (farmId: string) => void;
}

const STATUS_COLORS: Record<FarmMapStatus, string> = {
  healthy: "#7cc36b",
  watch: "#f0bc45",
  risk: "#f08a45",
  critical: "#f0695a",
  unknown: "#e5d7c4",
};

const COLORS = {
  contour: "229, 215, 196",
  river: "rgba(136, 144, 99, 0.6)",
  flow: "rgba(229, 215, 196, 0.7)",
  network: "rgba(229, 215, 196, 0.4)",
  sweep: "229, 215, 196",
  label: "rgba(53, 64, 36, 0.58)",
  labelText: "#e5d7c4",
  selectedLabel: "rgba(229, 215, 196, 0.9)",
  selectedLabelText: "#354024",
  edge: "#e5d7c4",
};

const HIT_RADIUS = 24;
/** Space kept clear inside the free area so pins and labels never touch the panels. */
const PADDING_X = 30;
const PADDING_Y = 20;
/** Smallest span, in degrees, so one farm or close farms still spread out. */
const MIN_SPAN = 0.6;
const CONTOUR_CELL = 14;
const RIVERS = [
  [[0.98, 0], [0.7, 0.3], [0.55, 0.45], [0.12, 1]],
  [[0.62, 0], [0.5, 0.25], [0.25, 0.4], [0, 0.78]],
];
/** Gap kept between labels so names never touch. */
const LABEL_GAP = 4;
// Marching squares: which cell edges a contour crosses, by corner pattern.
const SEGMENTS: Record<number, [string, string][]> = {
  1: [["l", "b"]], 2: [["b", "r"]], 3: [["l", "r"]], 4: [["t", "r"]],
  5: [["l", "t"], ["b", "r"]], 6: [["t", "b"]], 7: [["l", "t"]], 8: [["l", "t"]],
  9: [["t", "b"]], 10: [["t", "r"], ["l", "b"]], 11: [["t", "r"]], 12: [["l", "r"]],
  13: [["b", "r"]], 14: [["l", "b"]],
};

interface Contour {
  path: Path2D;
  alpha: number;
}

type Point = [number, number];

function terrain(x: number, y: number) {
  return (
    Math.sin(x * 2.1 + Math.sin(y * 1.7) * 1.3) * 0.5 +
    Math.sin(y * 2.7 - x * 1.1) * 0.35 +
    Math.sin((x + y) * 4.3) * 0.15
  );
}

function buildContours(width: number, height: number): Contour[] {
  const s = CONTOUR_CELL;
  const cols = Math.ceil(width / s) + 1;
  const rows = Math.ceil(height / s) + 1;
  const values: number[] = [];
  for (let j = 0; j < rows; j++)
    for (let i = 0; i < cols; i++) values[j * cols + i] = terrain((i * s) / 240, (j * s) / 240);

  const contours: Contour[] = [];
  for (let level = 0; level < 10; level++) {
    const k = -0.9 + level * 0.2;
    const path = new Path2D();
    for (let j = 0; j < rows - 1; j++) {
      for (let i = 0; i < cols - 1; i++) {
        const a = values[j * cols + i];
        const b = values[j * cols + i + 1];
        const c = values[(j + 1) * cols + i + 1];
        const d = values[(j + 1) * cols + i];
        const pattern = (a > k ? 8 : 0) | (b > k ? 4 : 0) | (c > k ? 2 : 0) | (d > k ? 1 : 0);
        const segments = SEGMENTS[pattern];
        if (!segments) continue;
        const x = i * s;
        const y = j * s;
        const edge: Record<string, Point> = {
          t: [x + (s * (k - a)) / (b - a), y],
          r: [x + s, y + (s * (k - b)) / (c - b)],
          b: [x + (s * (k - d)) / (c - d), y + s],
          l: [x, y + (s * (k - a)) / (d - a)],
        };
        for (const [from, to] of segments) {
          path.moveTo(edge[from][0], edge[from][1]);
          path.lineTo(edge[to][0], edge[to][1]);
        }
      }
    }
    contours.push({ path, alpha: Math.min(0.6, (0.05 + level * 0.022) * 1.3) });
  }
  return contours;
}

export function createFarmMap(canvas: HTMLCanvasElement, options: FarmMapOptions) {
  const context = canvas.getContext("2d");
  if (!context) return null;
  const ctx = context;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let contours: Contour[] = [];
  let width = 0;
  let height = 0;
  let ratio = 1;
  let state: FarmMapState = { farms: [], selectedId: null, rtl: false };
  let frame = 0;
  let visible = true;
  let hoveredId: string | null = null;
  const startedAt = performance.now();

  const area = () => options.getArea(width, height);

  /** A farm's spot in CSS pixels, fitted to the farms' own spread inside the free area. */
  const pointOf = (farm: FarmMapFarm): Point => {
    const lats = state.farms.map((item) => item.latitude);
    const lngs = state.farms.map((item) => item.longitude);
    const latMid = (Math.min(...lats) + Math.max(...lats)) / 2;
    const lngMid = (Math.min(...lngs) + Math.max(...lngs)) / 2;
    const latSpan = Math.max(MIN_SPAN, Math.max(...lats) - Math.min(...lats));
    const lngSpan = Math.max(MIN_SPAN, Math.max(...lngs) - Math.min(...lngs));
    const rawAcross = 0.5 + (farm.longitude - lngMid) / lngSpan;
    const across = state.rtl ? 1 - rawAcross : rawAcross;
    const down = 0.5 - (farm.latitude - latMid) / latSpan;
    const { x0, y0, x1, y1 } = area();
    return [
      x0 + PADDING_X + (x1 - x0 - PADDING_X * 2) * across,
      y0 + PADDING_Y + (y1 - y0 - PADDING_Y * 2) * down,
    ];
  };

  const drawGround = (t: number) => {
    ctx.lineWidth = 1;
    for (const contour of contours) {
      ctx.strokeStyle = `rgba(${COLORS.contour}, ${contour.alpha})`;
      ctx.stroke(contour.path);
    }
    for (const river of RIVERS) {
      ctx.beginPath();
      ctx.moveTo(river[0][0] * width, river[0][1] * height);
      ctx.bezierCurveTo(
        river[1][0] * width, river[1][1] * height,
        river[2][0] * width, river[2][1] * height,
        river[3][0] * width, river[3][1] * height
      );
      ctx.lineCap = "round";
      ctx.setLineDash([]);
      ctx.strokeStyle = COLORS.river;
      ctx.lineWidth = 7;
      ctx.stroke();
      ctx.setLineDash([2, 16]);
      ctx.lineDashOffset = -t * 0.02;
      ctx.strokeStyle = COLORS.flow;
      ctx.lineWidth = 1.6;
      ctx.stroke();
    }
    ctx.setLineDash([]);
  };

  const draw = (t: number) => {
    if (!width) return;
    const { farms, selectedId } = state;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.direction = "ltr";
    ctx.textAlign = "left";
    drawGround(t);
    if (!farms.length) return;

    const points = farms.map(pointOf);
    if (points.length > 1) {
      ctx.strokeStyle = COLORS.network;
      ctx.lineWidth = 1.2;
      ctx.setLineDash([4, 7]);
      ctx.lineDashOffset = -t * 0.012;
      ctx.beginPath();
      points.forEach(([x, y], index) => (index ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      if (points.length > 2) ctx.closePath();
      ctx.stroke();
      ctx.setLineDash([]);
    }

    const selectedIndex = Math.max(0, farms.findIndex((farm) => farm.id === selectedId));
    const [sx, sy] = points[selectedIndex];
    const radius = Math.min(150, width * 0.2);
    if ("createConicGradient" in ctx) {
      const sweep = ctx.createConicGradient(t / 1400, sx, sy);
      sweep.addColorStop(0, `rgba(${COLORS.sweep}, 0.26)`);
      sweep.addColorStop(0.14, `rgba(${COLORS.sweep}, 0)`);
      sweep.addColorStop(1, `rgba(${COLORS.sweep}, 0)`);
      ctx.fillStyle = sweep;
      ctx.beginPath();
      ctx.arc(sx, sy, radius, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.strokeStyle = `rgba(${COLORS.sweep}, 0.14)`;
    for (const r of [radius * 0.4, radius * 0.7, radius]) {
      ctx.beginPath();
      ctx.arc(sx, sy, r, 0, Math.PI * 2);
      ctx.stroke();
    }

    // Every farm pulses where it is.
    farms.forEach((farm, index) => {
      const [x, y] = points[index];
      ctx.strokeStyle = STATUS_COLORS[farm.status];
      ctx.lineWidth = 2;
      for (let ring = 0; ring < 2; ring++) {
        const phase = (t / 2400 + ring * 0.5 + index * 0.13) % 1;
        ctx.globalAlpha = (1 - phase) * 0.75;
        ctx.beginPath();
        ctx.arc(x, y, 9 + phase * 30, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    });

    farms.forEach((farm, index) => {
      const [x, y] = points[index];
      const selected = index === selectedIndex;
      const color = STATUS_COLORS[farm.status];
      ctx.shadowColor = color;
      ctx.shadowBlur = 18;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, selected ? 11 : 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = COLORS.edge;
      ctx.lineWidth = selected ? 3 : 2;
      ctx.stroke();
    });

    // Labels: the chosen farm first, then the hovered one, then the rest in
    // order, each skipped if it would overlap a label already placed.
    const font = getComputedStyle(canvas).fontFamily;
    const rightEdge = Math.min(width, area().x1 + 24);
    const placed: [number, number, number, number][] = [];
    const hoveredIndex = farms.findIndex((farm) => farm.id === hoveredId);
    const order = [selectedIndex, hoveredIndex, ...farms.map((_, index) => index)].filter(
      (index, position, list) => index >= 0 && list.indexOf(index) === position
    );
    ctx.font = `600 13px ${font}`;
    ctx.textBaseline = "middle";
    for (const index of order) {
      const farm = farms[index];
      const [x, y] = points[index];
      const selected = index === selectedIndex;
      const textWidth = ctx.measureText(farm.name).width;
      const boxWidth = textWidth + 16;
      const preferred = x + 22 + boxWidth > rightEdge ? x - 22 - boxWidth : x + 22;
      // Keep the label inside the map on both sides, even for very long names.
      const lx = Math.max(4, Math.min(preferred, width - boxWidth - 4));
      const box: [number, number, number, number] = [lx, y - 15, lx + boxWidth, y + 15];
      const overlaps = placed.some(
        ([l, t2, r, b]) =>
          box[0] < r + LABEL_GAP && box[2] > l - LABEL_GAP && box[1] < b + LABEL_GAP && box[3] > t2 - LABEL_GAP
      );
      if (overlaps && index !== selectedIndex && index !== hoveredIndex) continue;
      placed.push(box);
      ctx.fillStyle = selected ? COLORS.selectedLabel : COLORS.label;
      ctx.beginPath();
      ctx.roundRect(lx, y - 15, boxWidth, 30, 15);
      ctx.fill();
      ctx.fillStyle = selected ? COLORS.selectedLabelText : COLORS.labelText;
      ctx.fillText(farm.name, lx + 8, y + 1);
    }
  };

  const render = () => draw(reduceMotion ? 6000 : performance.now() - startedAt);

  const loop = () => {
    frame = requestAnimationFrame(loop);
    if (visible && !document.hidden) render();
  };

  const resize = () => {
    const box = canvas.getBoundingClientRect();
    if (!box.width) return;
    ratio = Math.min(2, window.devicePixelRatio || 1);
    width = box.width;
    height = box.height;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    contours = buildContours(width, height);
    render();
  };

  const farmAt = (event: MouseEvent) => {
    const box = canvas.getBoundingClientRect();
    const x = event.clientX - box.left;
    const y = event.clientY - box.top;
    return state.farms.find((farm) => {
      const [px, py] = pointOf(farm);
      return Math.hypot(px - x, py - y) < HIT_RADIUS;
    });
  };

  const handleClick = (event: MouseEvent) => {
    const farm = farmAt(event);
    if (farm) options.onSelect(farm.id);
  };
  const handleMove = (event: MouseEvent) => {
    const farm = farmAt(event);
    canvas.style.cursor = farm ? "pointer" : "default";
    if ((farm?.id ?? null) === hoveredId) return;
    hoveredId = farm?.id ?? null;
    render();
  };
  const handleLeave = () => {
    hoveredId = null;
    render();
  };

  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(canvas);
  const visibilityObserver = new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
  });
  visibilityObserver.observe(canvas);
  canvas.addEventListener("click", handleClick);
  canvas.addEventListener("mousemove", handleMove);
  canvas.addEventListener("mouseleave", handleLeave);
  resize();
  if (!reduceMotion) frame = requestAnimationFrame(loop);

  return {
    update(next: FarmMapState) {
      state = next;
      render();
    },
    destroy() {
      cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      visibilityObserver.disconnect();
      canvas.removeEventListener("click", handleClick);
      canvas.removeEventListener("mousemove", handleMove);
      canvas.removeEventListener("mouseleave", handleLeave);
    },
  };
}

export type FarmMapController = NonNullable<ReturnType<typeof createFarmMap>>;
