const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- REST helpers ---

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function command(cmd: string, args: Record<string, unknown> = {}) {
  return request<{ result: string }>("/api/command", {
    method: "POST",
    body: JSON.stringify({ command: cmd, args }),
  });
}

// --- Connection ---

export async function connect(): Promise<{ status: string; name?: string }> {
  const res = await request<{ status: string; address?: string }>("/api/connect", {
    method: "POST",
  });
  return { status: res.status, name: res.address ?? "Dash" };
}

export async function disconnect(): Promise<{ status: string }> {
  return request("/api/disconnect", { method: "POST" });
}

export async function getStatus(): Promise<{
  connected: boolean;
  name: string | null;
}> {
  const res = await request<{
    connected: boolean;
    no_robot_mode: boolean;
    sensors: Record<string, unknown>;
  }>("/api/status");
  return { connected: res.connected, name: res.connected ? "Dash" : null };
}

// --- Movement ---

export async function move(distance_mm: number, speed?: number) {
  return command("move", { distance_mm, speed_mmps: speed ?? 100 });
}

export async function turn(degrees: number) {
  return command("turn", { degrees });
}

export async function drive(speed: number) {
  return command("drive", { speed });
}

export async function spin(speed: number) {
  return command("spin", { speed });
}

export async function stop() {
  return command("stop");
}

// --- Lights ---

export async function setNeckColor(r: number, g: number, b: number) {
  const hex = `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
  return command("neck_color", { color: hex });
}

export async function setLeftEarColor(r: number, g: number, b: number) {
  const hex = `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
  return command("left_ear_color", { color: hex });
}

export async function setRightEarColor(r: number, g: number, b: number) {
  const hex = `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
  return command("right_ear_color", { color: hex });
}

export async function setEyeBrightness(brightness: number) {
  return command("eye_brightness", { value: brightness });
}

export async function setTailBrightness(brightness: number) {
  return command("tail_brightness", { value: brightness });
}

export async function setAllLights(r: number, g: number, b: number) {
  const hex = `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
  return command("all_lights", { color: hex });
}

// --- Sounds ---

export interface SoundInfo {
  name: string;
  category: string;
}

const SOUND_CATEGORIES: Record<string, string> = {
  hi: "Voices", bragging: "Voices", ohno: "Voices", ayayay: "Voices",
  confused: "Voices", huh: "Voices", okay: "Voices", yawn: "Voices",
  tada: "Voices", wee: "Voices", bye: "Voices", charge: "Voices",
  elephant: "Animals", horse: "Animals", cat: "Animals", dog: "Animals",
  dino: "Animals", lion: "Animals", goat: "Animals", croc: "Animals",
  siren: "Vehicles", horn: "Vehicles", engine: "Vehicles", tires: "Vehicles",
  helicopter: "Vehicles", jet: "Vehicles", boat: "Vehicles", train: "Vehicles",
  beep: "Effects", laser: "Effects", gobble: "Effects", buzz: "Effects",
  squeek: "Effects",
};

export async function getSounds(): Promise<SoundInfo[]> {
  const res = await request<{ sounds: string[] }>("/api/sounds");
  return res.sounds.map((name) => ({
    name,
    category: SOUND_CATEGORIES[name] || "Other",
  }));
}

export async function playSound(name: string) {
  return command("say", { sound: name });
}

// --- Chat ---

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  actions?: string[];
}

export async function chat(
  message: string,
  _history?: ChatMessage[]
): Promise<ChatMessage> {
  const res = await request<{
    response: string | null;
    error?: string;
    commands_executed: { command: string; args: Record<string, unknown>; result: string }[];
  }>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });

  if (res.error) {
    return { role: "assistant", content: res.error };
  }

  // Strip the ```commands blocks from the displayed text
  const cleanContent = (res.response ?? "").replace(/```commands\s*\n[\s\S]*?```/g, "").trim();

  const actions = res.commands_executed.map(
    (c) => `${c.command}(${JSON.stringify(c.args)}) -> ${c.result}`
  );

  return {
    role: "assistant",
    content: cleanContent || "(executed commands)",
    actions: actions.length > 0 ? actions : undefined,
  };
}

// --- Sensors WebSocket ---

export interface SensorData {
  proximity_left: number;
  proximity_right: number;
  proximity_rear: number;
  picked_up: boolean;
  clap_detected: boolean;
  head_pitch: number;
  head_yaw: number;
  wheel_distance_left: number;
  wheel_distance_right: number;
  tilt_x: number;
  tilt_y: number;
  tilt_z: number;
}

export type SensorCallback = (data: SensorData) => void;

function mapSensorData(raw: Record<string, unknown>): SensorData {
  return {
    proximity_left: Number(raw.prox_left ?? raw.proximity_left ?? 0),
    proximity_right: Number(raw.prox_right ?? raw.proximity_right ?? 0),
    proximity_rear: Number(raw.prox_rear ?? raw.proximity_rear ?? 0),
    picked_up: Boolean(raw.picked_up ?? false),
    clap_detected: Boolean(raw.clap ?? raw.clap_detected ?? false),
    head_pitch: Number(raw.head_pitch ?? 0),
    head_yaw: Number(raw.head_yaw ?? 0),
    wheel_distance_left: Number(raw.left_wheel ?? raw.wheel_distance_left ?? 0),
    wheel_distance_right: Number(raw.right_wheel ?? raw.wheel_distance_right ?? 0),
    tilt_x: Number(raw.pitch ?? raw.tilt_x ?? 0),
    tilt_y: Number(raw.roll ?? raw.tilt_y ?? 0),
    tilt_z: Number(raw.yaw ?? raw.tilt_z ?? 0),
  };
}

export function createSensorSocket(onData: SensorCallback): {
  close: () => void;
} {
  const wsBase = API_BASE.replace(/^http/, "ws");
  let ws: WebSocket | null = null;
  let closed = false;
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

  function connectWs() {
    if (closed) return;
    try {
      ws = new WebSocket(`${wsBase}/ws`);
      ws.onmessage = (event) => {
        try {
          const raw = JSON.parse(event.data);
          onData(mapSensorData(raw));
        } catch {
          // ignore parse errors
        }
      };
      ws.onclose = () => {
        if (!closed) {
          reconnectTimeout = setTimeout(connectWs, 3000);
        }
      };
      ws.onerror = () => {
        ws?.close();
      };
    } catch {
      if (!closed) {
        reconnectTimeout = setTimeout(connectWs, 3000);
      }
    }
  }

  connectWs();

  return {
    close() {
      closed = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      ws?.close();
    },
  };
}
