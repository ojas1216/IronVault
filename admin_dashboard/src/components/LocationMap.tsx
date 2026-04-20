import React from 'react';
import { MapContainer, TileLayer, CircleMarker, Polyline, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

interface LocationPoint {
  lat: number;
  lng: number;
  time: string;
  address?: string;
}

export const LocationMap: React.FC<{ locations: LocationPoint[] }> = ({ locations }) => {
  if (!locations.length) {
    return (
      <div className="h-64 bg-gray-50 rounded-lg flex items-center justify-center text-gray-500">
        No location data available
      </div>
    );
  }

  const center: [number, number] = [locations[0].lat, locations[0].lng];
  const path: [number, number][] = locations.map((l) => [l.lat, l.lng]);

  return (
    <div className="h-72 rounded-lg overflow-hidden">
      <MapContainer center={center} zoom={14} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; OpenStreetMap contributors'
        />
        <Polyline positions={path} color="#1565C0" weight={2} />
        {locations.slice(0, 10).map((loc, i) => (
          <CircleMarker key={i} center={[loc.lat, loc.lng]} radius={8} color="#1565C0" fillOpacity={0.8}>
            <Popup>
              <p className="text-xs">{new Date(loc.time).toLocaleString()}</p>
              {loc.address && <p className="text-xs text-gray-600">{loc.address}</p>}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
};
