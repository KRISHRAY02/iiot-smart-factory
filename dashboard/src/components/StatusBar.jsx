export default function StatusBar({ status, wsConnected }) {
  const mqttOk = status?.mqtt_connected;
  const influxOk = status?.influx_connected;

  return (
    <>
      <span className={`status-pill ${wsConnected ? "ok" : "down"}`}>
        Live feed {wsConnected ? "connected" : "disconnected"}
      </span>
      <span className={`status-pill ${mqttOk ? "ok" : "down"}`}>
        MQTT {mqttOk ? "up" : "down"}
      </span>
      <span className={`status-pill ${influxOk ? "ok" : "down"}`}>
        Database {influxOk ? "up" : "down"}
      </span>
    </>
  );
}
