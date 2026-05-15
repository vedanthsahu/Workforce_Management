import React, { useCallback, useEffect, useRef, useState } from "react";
import { Maximize2, ZoomIn, ZoomOut } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────
export interface SeatWithSvgId {
  id: string;
  svgId: string;
  label: string;
  status: "available" | "booked" | "unavailable" | "yours";
  matchesPreferences: boolean;
  amenities: string[];
}

// ─── All seat <g> ids present in floor-IT.svg ────────────────────────────────
const ALL_SVG_SEAT_IDS = [
  "1","2","3","4","5","6","7","8","9","10",
  "11","12","13","14","15","16","17","18","19","20",
  "21","22","23","s24","25","26","27","28","29","30","31",
];

const SVG_W = 2466;
const SVG_H = 2039;

// ─── Color palettes ───────────────────────────────────────────────────────────
const PALETTES: Record<string, {
  body: string; bodyStroke: string;
  armrest: string;
  back: string; backStroke: string;
  curve: string; arc: string;
  opacity: string;
}> = {
  available: {
    body: "#d1fae5", bodyStroke: "#34d399",
    armrest: "#a7f3d0",
    back: "#059669", backStroke: "#047857",
    curve: "#34d399", arc: "#6ee7b7",
    opacity: "1",
  },
  selected: {
    body: "#4f46e5", bodyStroke: "#3730a3",
    armrest: "#6366f1",
    back: "#c7d2fe", backStroke: "#6366f1",
    curve: "#6366f1", arc: "#a5b4fc",
    opacity: "1",
  },
  booked: {
  body: "#fca5a5", bodyStroke: "#ef4444",
  armrest: "#f87171",
  back: "#dc2626", backStroke: "#b91c1c",
  curve: "#ef4444", arc: "#fca5a5",
  opacity: "0.85",
},
unavailable: {
  body: "#fca5a5", bodyStroke: "#ef4444",
  armrest: "#f87171",
  back: "#dc2626", backStroke: "#b91c1c",
  curve: "#ef4444", arc: "#fca5a5",
  opacity: "0.85",
},
  yours: {
    body: "#d1fae5", bodyStroke: "#10b981",
    armrest: "#6ee7b7",
    back: "#059669", backStroke: "#047857",
    curve: "#10b981", arc: "#6ee7b7",
    opacity: "1",
  },
  preference: {
    body: "#e0e7ff", bodyStroke: "#818cf8",
    armrest: "#c7d2fe",
    back: "#4f46e5", backStroke: "#3730a3",
    curve: "#818cf8", arc: "#a5b4fc",
    opacity: "1",
  },
//   unloaded: {
//     body: "#C8C8C8", bodyStroke: "#888888",
//     armrest: "#B0B0B0",
//     back: "#616161", backStroke: "#424242",
//     curve: "#707070", arc: "#A0A0A0",
//     opacity: "0.35",
//   },
unloaded: {
  body: "#fca5a5", bodyStroke: "#ef4444",
  armrest: "#f87171",
  back: "#dc2626", backStroke: "#b91c1c",
  curve: "#ef4444", arc: "#fca5a5",
  opacity: "0.85",
},
};

// ─── Recolor one seat block inside the raw SVG string ────────────────────────
function recolorSeat(svg: string, svgId: string, paletteKey: string): string {
  const p = PALETTES[paletteKey] ?? PALETTES.unloaded;

  const openTag = `<g id="${svgId}">`;
  const start   = svg.indexOf(openTag);
  if (start === -1) return svg;

  const end = svg.indexOf("</g>", start);
  if (end === -1) return svg;

  const before = svg.slice(0, start);
  let   block  = svg.slice(start, end + 4);
  const after  = svg.slice(end + 4);

  block = block.replace(
    /fill="#C8C8C8" stroke="#888888"/g,
    `fill="${p.body}" stroke="${p.bodyStroke}"`
  );
  block = block.replace(
    /fill="#B0B0B0" stroke="#888888"/g,
    `fill="${p.armrest}" stroke="${p.bodyStroke}"`
  );
  block = block.replace(
    /fill="#616161" stroke="#424242"/g,
    `fill="${p.back}" stroke="${p.backStroke}"`
  );
  block = block.replace(/stroke="#707070"/g, `stroke="${p.curve}"`);
  block = block.replace(/stroke="#A0A0A0"/g, `stroke="${p.arc}"`);
  block = block.replace(
    `<g id="${svgId}">`,
    `<g id="${svgId}" style="opacity:${p.opacity};cursor:${
      paletteKey === "available" || paletteKey === "yours" || paletteKey === "preference"
        ? "pointer"
        : "default"
    }">`
  );

  return before + block + after;
}

// ─── Build fully-colored SVG string ──────────────────────────────────────────
function buildColoredSvg(
  rawSvg: string,
  seats: SeatWithSvgId[],
  selectedSeatId: string | null
): string {
  const seatMap = new Map<string, SeatWithSvgId>();
  seats.forEach((s) => seatMap.set(s.svgId, s));

  let svg = rawSvg;
  ALL_SVG_SEAT_IDS.forEach((svgId) => {
    const seat = seatMap.get(svgId);
    let key: string;
    if (!seat) {
      key = "unloaded";
    } else if (seat.id === selectedSeatId) {
      key = "selected";
    } else if (seat.matchesPreferences && seat.status === "available") {
      key = "preference";
    } else {
      key = seat.status;
    }
    svg = recolorSeat(svg, svgId, key);
  });
  return svg;
}

// ─── Walk up the click target to find a seat svgId ───────────────────────────
function getSvgIdFromClick(target: EventTarget | null): string | null {
  let el = target as Element | null;
  while (el) {
    if (el.tagName?.toLowerCase() === "svg") return null;
    const id = el.getAttribute("id");
    if (id && ALL_SVG_SEAT_IDS.includes(id)) return id;
    el = el.parentElement;
  }
  return null;
}

// ─── Props ────────────────────────────────────────────────────────────────────
// interface SvgFloorMapPageProps {
//   seats: SeatWithSvgId[];
//   selectedSeatId: string | null;
//   // ── CHANGED: accepts null to support deselect ──────────────────────────
//   onSeatSelect: (seatId: string | null) => void;
//   loading?: boolean;
// }

interface SvgFloorMapPageProps {
  seats: SeatWithSvgId[];
  selectedSeatId: string | null;
  onSeatSelect: (seatId: string | null) => void;
  loading?: boolean;
  siteName?: string;
  buildingName?: string;
  floorName?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────
export const SvgFloorMapPage: React.FC<SvgFloorMapPageProps> = ({
  seats,
  selectedSeatId,
  onSeatSelect,
  loading = false,
}) => {
  const wrapperRef   = useRef<HTMLDivElement>(null);
  const transformRef = useRef<HTMLDivElement>(null);

  const scaleRef     = useRef(1);
  const translateRef = useRef({ x: 0, y: 0 });
  const isPanning    = useRef(false);
  const panStart     = useRef({ x: 0, y: 0 });
  const mouseDownPos = useRef({ x: 0, y: 0 });
  const didDrag      = useRef(false);

  const [rawSvg,      setRawSvg]      = useState<string | null>(null);
  const [svgError,    setSvgError]    = useState(false);
  const [zoomDisplay, setZoomDisplay] = useState(100);

  const coloredSvg = rawSvg
    ? buildColoredSvg(rawSvg, seats, selectedSeatId)
    : null;

  // ── Fetch raw SVG once ────────────────────────────────────────────────────
  useEffect(() => {
    fetch("/floor-IT.svg")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then(setRawSvg)
      .catch(() => setSvgError(true));
  }, []);

  // ── applyTransform ────────────────────────────────────────────────────────
  const applyTransform = useCallback(() => {
    const el = transformRef.current;
    if (!el) return;
    el.style.transform = `translate(${translateRef.current.x}px,${translateRef.current.y}px) scale(${scaleRef.current})`;
  }, []);

  // ── fitView ───────────────────────────────────────────────────────────────
  const fitView = useCallback(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;
    const { width: wW, height: wH } = wrapper.getBoundingClientRect();
    const scale = Math.min(wW / SVG_W, wH / SVG_H);
    scaleRef.current     = scale;
    translateRef.current = {
      x: (wW - SVG_W * scale) / 2,
      y: (wH - SVG_H * scale) / 2,
    };
    applyTransform();
    setZoomDisplay(Math.round(scale * 100));
  }, [applyTransform]);

  useEffect(() => {
    if (rawSvg) fitView();
  }, [rawSvg, fitView]);

  // ── Zoom step ─────────────────────────────────────────────────────────────
  const zoomStep = useCallback((factor: number) => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;
    const { width: wW, height: wH } = wrapper.getBoundingClientRect();
    const oldScale = scaleRef.current;
    const newScale = Math.min(Math.max(oldScale * factor, 0.05), 4);
    const cx = wW / 2, cy = wH / 2;
    translateRef.current = {
      x: cx - (cx - translateRef.current.x) * (newScale / oldScale),
      y: cy - (cy - translateRef.current.y) * (newScale / oldScale),
    };
    scaleRef.current = newScale;
    applyTransform();
    setZoomDisplay(Math.round(newScale * 100));
  }, [applyTransform]);

  const zoomIn  = useCallback(() => zoomStep(1.25),     [zoomStep]);
  const zoomOut = useCallback(() => zoomStep(1 / 1.25), [zoomStep]);

  // ── Wheel zoom ────────────────────────────────────────────────────────────
  useEffect(() => {
    const el = wrapperRef.current;
    if (!el) return;
    const handler = (e: WheelEvent) => {
      e.preventDefault();
      const factor   = e.deltaY < 0 ? 1.1 : 1 / 1.1;
      const oldScale = scaleRef.current;
      const newScale = Math.min(Math.max(oldScale * factor, 0.05), 4);
      const rect     = el.getBoundingClientRect();
      translateRef.current = {
        x: (e.clientX - rect.left) -
           ((e.clientX - rect.left) - translateRef.current.x) * (newScale / oldScale),
        y: (e.clientY - rect.top) -
           ((e.clientY - rect.top)  - translateRef.current.y) * (newScale / oldScale),
      };
      scaleRef.current = newScale;
      applyTransform();
      setZoomDisplay(Math.round(newScale * 100));
    };
    el.addEventListener("wheel", handler, { passive: false });
    return () => el.removeEventListener("wheel", handler);
  }, [applyTransform]);

  // ── Pan handlers ──────────────────────────────────────────────────────────
  const onMouseDown = (e: React.MouseEvent) => {
    isPanning.current    = true;
    didDrag.current      = false;
    mouseDownPos.current = { x: e.clientX, y: e.clientY };
    panStart.current     = { ...translateRef.current };
    (e.currentTarget as HTMLElement).style.cursor = "grabbing";
  };

  const onMouseMove = (e: React.MouseEvent) => {
    if (!isPanning.current) return;
    const dx = e.clientX - mouseDownPos.current.x;
    const dy = e.clientY - mouseDownPos.current.y;
    if (!didDrag.current && (Math.abs(dx) > 4 || Math.abs(dy) > 4)) {
      didDrag.current = true;
    }
    if (didDrag.current) {
      translateRef.current = { x: panStart.current.x + dx, y: panStart.current.y + dy };
      applyTransform();
    }
  };

  const onMouseUp = (e: React.MouseEvent) => {
    isPanning.current = false;
    (e.currentTarget as HTMLElement).style.cursor = "grab";
  };

  // ── Click on SVG → select / deselect seat ────────────────────────────────
  const onMapClick = (e: React.MouseEvent) => {
    if (didDrag.current) {
      didDrag.current = false;
      return;
    }

    const svgId = getSvgIdFromClick(e.target);
    if (!svgId) return;

    const seat = seats.find((s) => s.svgId === svgId);
    if (!seat) return;

    // Only selectable if available or yours
    if (seat.status !== "available" && seat.status !== "yours") return;

    // ── CHANGED: toggle — clicking the already-selected seat deselects it ──
    if (seat.id === selectedSeatId) {
      onSeatSelect(null);
    } else {
      onSeatSelect(seat.id);
    }
  };

  // ─── Render ───────────────────────────────────────────────────────────────
  return (
    <div
      className="relative bg-[#F7F8FC] border border-[#EBEBF5] rounded-xl overflow-hidden"
      style={{ width: "100%", height: 520 }}
    >
      {/* Zoom controls */}
      <div className="absolute top-3 right-3 z-20 flex flex-col gap-1.5">
        {([
          { icon: <ZoomIn    size={14} />, action: zoomIn,  title: "Zoom in"     },
          { icon: <ZoomOut   size={14} />, action: zoomOut, title: "Zoom out"    },
          { icon: <Maximize2 size={14} />, action: fitView, title: "Fit to view" },
        ] as const).map(({ icon, action, title }) => (
          <button
            key={title}
            onClick={(e) => { e.stopPropagation(); action(); }}
            title={title}
            className="w-8 h-8 rounded-lg bg-white border border-[#EBEBF5] shadow-sm flex items-center justify-center hover:bg-gray-50 text-gray-600 transition-colors"
          >
            {icon}
          </button>
        ))}
      </div>

      {/* Zoom % */}
      <div className="absolute top-3 left-3 z-20 text-[10px] font-semibold text-gray-400 bg-white/80 px-2 py-1 rounded-md border border-[#EBEBF5] select-none tabular-nums">
        {zoomDisplay}%
      </div>

      {/* Legend */}
      <div className="absolute bottom-8 left-3 z-20 flex items-center gap-3 bg-white/80 px-3 py-1.5 rounded-md border border-[#EBEBF5] select-none">
        {[
          { color: "#059669", label: "Available"   },
        //   { color: "#4f46e5", label: "Preference"  },
        //   { color: "#6b7280", label: "Booked"      },
          { color: "#dc2626", label: "Unavailable" }, // updated to match new red palette
          { color: "#6366f1", label: "Selected"    },
        //   { color: "#10b981", label: "Yours"       },
        ].map(({ color, label }) => (
          <span key={label} className="flex items-center gap-1 text-[10px] text-gray-500">
            <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: color }} />
            {label}
          </span>
        ))}
      </div>

      {/* Hint */}
      <div className="absolute bottom-2 left-3 z-20 text-[10px] text-gray-400 bg-white/80 px-2 py-1 rounded-md border border-[#EBEBF5] select-none">
        Scroll to zoom · Drag to pan · Click a green seat to select / deselect
      </div>

      {/* Map viewport */}
      <div
        ref={wrapperRef}
        className="w-full h-full overflow-hidden select-none"
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        onClick={onMapClick}
        style={{ cursor: "grab" }}
      >
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#F7F8FC] z-10">
            <div className="flex flex-col items-center gap-3">
              <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
              <p className="text-[12.5px] text-gray-400">Loading floor plan…</p>
            </div>
          </div>
        )}

        {svgError && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <p className="text-[13px] text-gray-500 mb-1">Floor plan unavailable</p>
              <p className="text-[11.5px] text-gray-400">
                Place SVG at{" "}
                <code className="bg-gray-100 px-1 rounded">/public/floor-IT.svg</code>
              </p>
            </div>
          </div>
        )}

        {coloredSvg && !loading && (
          <div
            ref={transformRef}
            style={{
              transformOrigin: "top left",
              width: `${SVG_W}px`,
              height: `${SVG_H}px`,
              willChange: "transform",
            }}
            dangerouslySetInnerHTML={{ __html: coloredSvg }}
          />
        )}
      </div>
    </div>
  );
};

export default SvgFloorMapPage;
