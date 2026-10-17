interface LocationMapPreviewProps {
  latitude: number;
  longitude: number;
  title: string;
}

// OpenStreetMap's official embeddable map: no API key and no map library.
const OSM_EMBED_URL = "https://www.openstreetmap.org/export/embed.html";
const SPAN_DEGREES = 0.02;

export function LocationMapPreview({ latitude, longitude, title }: LocationMapPreviewProps) {
  const bbox = [
    longitude - SPAN_DEGREES,
    latitude - SPAN_DEGREES,
    longitude + SPAN_DEGREES,
    latitude + SPAN_DEGREES,
  ]
    .map((value) => value.toFixed(5))
    .join(",");
  const src = `${OSM_EMBED_URL}?bbox=${bbox}&layer=mapnik&marker=${latitude},${longitude}`;

  return (
    <iframe
      title={title}
      src={src}
      loading="lazy"
      referrerPolicy="no-referrer"
      sandbox="allow-scripts allow-same-origin"
      className="h-44 w-full rounded-lg border border-border bg-muted"
    />
  );
}
