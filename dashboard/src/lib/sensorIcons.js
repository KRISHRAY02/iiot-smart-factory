const SENSOR_ICONS = {
  temperature: "\u{1F321}️",
  pressure: "\u{1F4CF}",
  vibration: "\u{1F4C8}",
  humidity: "\u{1F4A7}",
};

export function iconFor(sensorType) {
  return SENSOR_ICONS[sensorType] || "\u{1F4CA}";
}
