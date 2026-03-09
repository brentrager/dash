"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import * as api from "./lib/api";
import type { SensorData, ChatMessage } from "./lib/api";

// ---------------------------------------------------------------------------
// Reusable Card wrapper
// ---------------------------------------------------------------------------
function Card({
  title,
  accentColor = "text-neon-cyan",
  children,
  className = "",
}: {
  title: string;
  accentColor?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`bg-card-bg border border-card-border rounded-2xl p-4 flex flex-col gap-3 ${className}`}
    >
      <h2 className={`text-sm font-bold uppercase tracking-widest ${accentColor}`}>
        {title}
      </h2>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Toast / notification banner
// ---------------------------------------------------------------------------
function Toast({
  message,
  type,
  onDismiss,
}: {
  message: string;
  type: "error" | "success";
  onDismiss: () => void;
}) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 4000);
    return () => clearTimeout(t);
  }, [onDismiss]);

  return (
    <div
      className={`fixed top-4 right-4 z-50 px-4 py-2 rounded-xl text-sm font-medium shadow-lg transition-all ${
        type === "error"
          ? "bg-red-900/80 text-red-200 border border-red-700"
          : "bg-green-900/80 text-green-200 border border-green-700"
      }`}
    >
      {message}
      <button onClick={onDismiss} className="ml-3 opacity-60 hover:opacity-100">
        x
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Proximity Bar
// ---------------------------------------------------------------------------
function ProximityBar({
  label,
  value,
  max = 400,
  color,
}: {
  label: string;
  value: number;
  max?: number;
  color: string;
}) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs w-10 text-right font-mono opacity-70">{label}</span>
      <div className="flex-1 h-3 bg-[#1a1a1a] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-xs w-8 font-mono">{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------
export default function Dashboard() {
  // --- State ---
  const [connected, setConnected] = useState(false);
  const [robotName, setRobotName] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [toast, setToast] = useState<{
    message: string;
    type: "error" | "success";
  } | null>(null);

  // Movement
  const [speed, setSpeed] = useState(80);
  const [distanceMm, setDistanceMm] = useState(200);
  const [turnDeg, setTurnDeg] = useState(90);

  // Lights
  const [neckColor, setNeckColor] = useState("#00ffff");
  const [earColor, setEarColor] = useState("#ff00ff");
  const [eyeBrightness, setEyeBrightness] = useState(255);
  const [tailBrightness, setTailBrightness] = useState(255);

  // Sounds
  const [sounds, setSounds] = useState<api.SoundInfo[]>([]);

  // Sensors
  const [sensors, setSensors] = useState<SensorData>({
    proximity_left: 0,
    proximity_right: 0,
    proximity_rear: 0,
    picked_up: false,
    clap_detected: false,
    head_pitch: 0,
    head_yaw: 0,
    wheel_distance_left: 0,
    wheel_distance_right: 0,
    tilt_x: 0,
    tilt_y: 0,
    tilt_z: 0,
  });

  // Chat
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // --- Helpers ---
  const showToast = useCallback(
    (message: string, type: "error" | "success" = "error") => {
      setToast({ message, type });
    },
    []
  );

  const safeCall = useCallback(
    async <T,>(fn: () => Promise<T>, successMsg?: string): Promise<T | null> => {
      try {
        const result = await fn();
        if (successMsg) showToast(successMsg, "success");
        return result;
      } catch (e) {
        showToast(e instanceof Error ? e.message : "Request failed");
        return null;
      }
    },
    [showToast]
  );

  // --- Fetch status + sounds on mount ---
  useEffect(() => {
    api
      .getStatus()
      .then((s) => {
        setConnected(s.connected);
        setRobotName(s.name);
      })
      .catch(() => {});

    api
      .getSounds()
      .then(setSounds)
      .catch(() => {
        // Fallback sounds from constants
        const fallback: api.SoundInfo[] = [
          // Voices
          { name: "hi", category: "Voices" },
          { name: "bragging", category: "Voices" },
          { name: "ohno", category: "Voices" },
          { name: "ayayay", category: "Voices" },
          { name: "confused", category: "Voices" },
          { name: "huh", category: "Voices" },
          { name: "okay", category: "Voices" },
          { name: "yawn", category: "Voices" },
          { name: "tada", category: "Voices" },
          { name: "wee", category: "Voices" },
          { name: "bye", category: "Voices" },
          { name: "charge", category: "Voices" },
          // Animals
          { name: "elephant", category: "Animals" },
          { name: "horse", category: "Animals" },
          { name: "cat", category: "Animals" },
          { name: "dog", category: "Animals" },
          { name: "dino", category: "Animals" },
          { name: "lion", category: "Animals" },
          { name: "goat", category: "Animals" },
          { name: "croc", category: "Animals" },
          // Vehicles
          { name: "siren", category: "Vehicles" },
          { name: "horn", category: "Vehicles" },
          { name: "engine", category: "Vehicles" },
          { name: "tires", category: "Vehicles" },
          { name: "helicopter", category: "Vehicles" },
          { name: "jet", category: "Vehicles" },
          { name: "boat", category: "Vehicles" },
          { name: "train", category: "Vehicles" },
          // Effects
          { name: "beep", category: "Effects" },
          { name: "laser", category: "Effects" },
          { name: "gobble", category: "Effects" },
          { name: "buzz", category: "Effects" },
          { name: "squeek", category: "Effects" },
        ];
        setSounds(fallback);
      });
  }, []);

  // --- WebSocket for sensors ---
  useEffect(() => {
    const socket = api.createSensorSocket((data) => setSensors(data));
    return () => socket.close();
  }, []);

  // --- Arrow key movement ---
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Skip if user is typing in an input/textarea
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;

      switch (e.key) {
        case "ArrowUp":
          e.preventDefault();
          safeCall(() => api.move(distanceMm, speed));
          break;
        case "ArrowDown":
          e.preventDefault();
          safeCall(() => api.move(-distanceMm, speed));
          break;
        case "ArrowLeft":
          e.preventDefault();
          safeCall(() => api.turn(-turnDeg));
          break;
        case "ArrowRight":
          e.preventDefault();
          safeCall(() => api.turn(turnDeg));
          break;
        case " ":
          e.preventDefault();
          safeCall(() => api.stop());
          break;
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [distanceMm, speed, turnDeg, safeCall]);

  // --- Auto-scroll chat ---
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // --- Handlers ---
  const handleConnect = async () => {
    setConnecting(true);
    if (connected) {
      await safeCall(() => api.disconnect(), "Disconnected");
      setConnected(false);
      setRobotName(null);
    } else {
      const res = await safeCall(() => api.connect(), "Connected!");
      if (res) {
        setConnected(true);
        setRobotName(res.name ?? "Dash");
      }
    }
    setConnecting(false);
  };

  const hexToRgb = (hex: string) => {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return { r, g, b };
  };

  const handleNeckColor = (color: string) => {
    setNeckColor(color);
    const { r, g, b } = hexToRgb(color);
    safeCall(() => api.setNeckColor(r, g, b));
  };

  const handleEarColor = (color: string) => {
    setEarColor(color);
    const { r, g, b } = hexToRgb(color);
    safeCall(() => api.setLeftEarColor(r, g, b));
    safeCall(() => api.setRightEarColor(r, g, b));
  };

  const handleEyeBrightness = (val: number) => {
    setEyeBrightness(val);
    safeCall(() => api.setEyeBrightness(val));
  };

  const handleTailBrightness = (val: number) => {
    setTailBrightness(val);
    safeCall(() => api.setTailBrightness(val));
  };

  const handlePreset = async (preset: string) => {
    const presets: Record<
      string,
      { neck: string; ears: string; eye: number; tail: number }
    > = {
      Rainbow: { neck: "#ff0000", ears: "#0000ff", eye: 255, tail: 255 },
      Party: { neck: "#ff00ff", ears: "#ffff00", eye: 255, tail: 255 },
      Alert: { neck: "#ff0000", ears: "#ff0000", eye: 255, tail: 0 },
      Calm: { neck: "#0044ff", ears: "#003388", eye: 80, tail: 60 },
    };
    const p = presets[preset];
    if (!p) return;
    setNeckColor(p.neck);
    setEarColor(p.ears);
    setEyeBrightness(p.eye);
    setTailBrightness(p.tail);
    const n = hexToRgb(p.neck);
    const e = hexToRgb(p.ears);
    await Promise.all([
      safeCall(() => api.setNeckColor(n.r, n.g, n.b)),
      safeCall(() => api.setLeftEarColor(e.r, e.g, e.b)),
      safeCall(() => api.setRightEarColor(e.r, e.g, e.b)),
      safeCall(() => api.setEyeBrightness(p.eye)),
      safeCall(() => api.setTailBrightness(p.tail)),
    ]);
  };

  const handleChat = async () => {
    if (!chatInput.trim() || chatLoading) return;
    const userMsg: ChatMessage = { role: "user", content: chatInput.trim() };
    setChatHistory((prev) => [...prev, userMsg]);
    setChatInput("");
    setChatLoading(true);
    const res = await safeCall(() =>
      api.chat(userMsg.content, [...chatHistory, userMsg])
    );
    if (res) {
      setChatHistory((prev) => [...prev, res]);
    }
    setChatLoading(false);
  };

  // --- Sound categories ---
  const soundCategories = sounds.reduce<Record<string, api.SoundInfo[]>>(
    (acc, s) => {
      const cat = s.category || "Other";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(s);
      return acc;
    },
    {}
  );

  // === RENDER ===
  return (
    <div className="min-h-screen p-3 md:p-5 flex flex-col gap-4 max-w-[1600px] mx-auto">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDismiss={() => setToast(null)}
        />
      )}

      {/* === CONNECTION BAR === */}
      <div className="bg-card-bg border border-card-border rounded-2xl px-5 py-3 flex items-center gap-4 flex-wrap relative">
        <div
          className={`w-3 h-3 rounded-full ${
            connected ? "bg-green-400 pulse-green" : "bg-red-500 pulse-red"
          }`}
        />
        <span className="text-sm font-mono opacity-70">
          {connected
            ? `Connected to ${robotName ?? "Dash"}`
            : "Not connected"}
        </span>
        <button
          onClick={handleConnect}
          disabled={connecting}
          className={`neon-btn ml-auto px-5 py-2 rounded-xl text-sm font-bold transition-all ${
            connected
              ? "bg-red-900/50 text-red-300 border border-red-700 hover:bg-red-800/50"
              : "bg-cyan-900/50 text-neon-cyan border border-cyan-700 hover:bg-cyan-800/50"
          } disabled:opacity-50`}
        >
          {connecting ? "..." : connected ? "Disconnect" : "Connect"}
        </button>
        <h1 className="w-full text-center text-2xl font-bold bg-gradient-to-r from-neon-cyan via-neon-magenta to-neon-lime bg-clip-text text-transparent order-first md:order-none md:w-auto md:absolute md:left-1/2 md:-translate-x-1/2">
          Dash Robot Controller
        </h1>
      </div>

      {/* === MAIN GRID === */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 flex-1">
        {/* --- MOVEMENT CONTROLS --- */}
        <Card title="Movement" accentColor="text-neon-cyan">
          {/* Direction buttons */}
          <div className="grid grid-cols-3 gap-2 max-w-[180px] mx-auto">
            <div />
            <button
              onClick={() => safeCall(() => api.move(distanceMm, speed))}
              className="neon-btn bg-cyan-900/40 text-neon-cyan border border-cyan-800 rounded-xl p-3 text-lg"
              aria-label="Forward"
            >
              &#9650;
            </button>
            <div />
            <button
              onClick={() => safeCall(() => api.turn(-turnDeg))}
              className="neon-btn bg-cyan-900/40 text-neon-cyan border border-cyan-800 rounded-xl p-3 text-lg"
              aria-label="Left"
            >
              &#9664;
            </button>
            <button
              onClick={() => safeCall(() => api.stop())}
              className="neon-btn bg-red-900/40 text-red-400 border border-red-800 rounded-xl p-3 text-xs font-bold"
            >
              STOP
            </button>
            <button
              onClick={() => safeCall(() => api.turn(turnDeg))}
              className="neon-btn bg-cyan-900/40 text-neon-cyan border border-cyan-800 rounded-xl p-3 text-lg"
              aria-label="Right"
            >
              &#9654;
            </button>
            <div />
            <button
              onClick={() => safeCall(() => api.move(-distanceMm, speed))}
              className="neon-btn bg-cyan-900/40 text-neon-cyan border border-cyan-800 rounded-xl p-3 text-lg"
              aria-label="Back"
            >
              &#9660;
            </button>
            <div />
          </div>

          {/* Speed slider */}
          <label className="flex flex-col gap-1">
            <span className="text-xs opacity-60">Speed: {speed}</span>
            <input
              type="range"
              min={10}
              max={200}
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
            />
          </label>

          {/* Distance input */}
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={distanceMm}
              onChange={(e) => setDistanceMm(Number(e.target.value))}
              className="w-20 bg-[#1a1a1a] border border-[#333] rounded-lg px-2 py-1 text-sm font-mono text-center"
            />
            <span className="text-xs opacity-50">mm</span>
            <button
              onClick={() => safeCall(() => api.move(distanceMm, speed))}
              className="neon-btn ml-auto px-3 py-1 bg-cyan-900/40 text-neon-cyan border border-cyan-800 rounded-lg text-xs font-bold"
            >
              GO
            </button>
          </div>

          {/* Turn input */}
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={turnDeg}
              onChange={(e) => setTurnDeg(Number(e.target.value))}
              className="w-20 bg-[#1a1a1a] border border-[#333] rounded-lg px-2 py-1 text-sm font-mono text-center"
            />
            <span className="text-xs opacity-50">deg</span>
            <button
              onClick={() => safeCall(() => api.turn(turnDeg))}
              className="neon-btn ml-auto px-3 py-1 bg-cyan-900/40 text-neon-cyan border border-cyan-800 rounded-lg text-xs font-bold"
            >
              TURN
            </button>
          </div>
        </Card>

        {/* --- LIGHTS PANEL --- */}
        <Card title="Lights" accentColor="text-neon-magenta">
          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col items-center gap-1">
              <span className="text-xs opacity-60">Neck</span>
              <input
                type="color"
                value={neckColor}
                onChange={(e) => handleNeckColor(e.target.value)}
                className="w-12 h-12 rounded-lg"
              />
            </label>
            <label className="flex flex-col items-center gap-1">
              <span className="text-xs opacity-60">Ears</span>
              <input
                type="color"
                value={earColor}
                onChange={(e) => handleEarColor(e.target.value)}
                className="w-12 h-12 rounded-lg"
              />
            </label>
          </div>

          <label className="flex flex-col gap-1">
            <span className="text-xs opacity-60">
              Eye brightness: {eyeBrightness}
            </span>
            <input
              type="range"
              min={0}
              max={255}
              value={eyeBrightness}
              onChange={(e) => handleEyeBrightness(Number(e.target.value))}
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-xs opacity-60">
              Tail brightness: {tailBrightness}
            </span>
            <input
              type="range"
              min={0}
              max={255}
              value={tailBrightness}
              onChange={(e) => handleTailBrightness(Number(e.target.value))}
            />
          </label>

          <button
            onClick={() => {
              const { r, g, b } = hexToRgb(neckColor);
              safeCall(() => api.setAllLights(r, g, b));
            }}
            className="neon-btn w-full py-2 bg-purple-900/40 text-neon-magenta border border-purple-800 rounded-xl text-sm font-bold"
          >
            All Lights = Neck Color
          </button>

          <div className="grid grid-cols-2 gap-2">
            {["Rainbow", "Party", "Alert", "Calm"].map((preset) => (
              <button
                key={preset}
                onClick={() => handlePreset(preset)}
                className="neon-btn py-2 bg-[#1a1a1a] border border-[#333] rounded-xl text-xs font-bold hover:border-neon-magenta hover:text-neon-magenta transition-colors"
              >
                {preset}
              </button>
            ))}
          </div>
        </Card>

        {/* --- SOUNDS PANEL --- */}
        <Card title="Sounds" accentColor="text-neon-lime">
          <div className="overflow-y-auto max-h-[400px] flex flex-col gap-3 pr-1">
            {Object.entries(soundCategories).map(([category, items]) => (
              <div key={category}>
                <h3 className="text-xs font-bold uppercase tracking-wider opacity-50 mb-1">
                  {category}
                </h3>
                <div className="grid grid-cols-3 gap-1.5">
                  {items.map((s) => (
                    <button
                      key={s.name}
                      onClick={() => safeCall(() => api.playSound(s.name))}
                      className="neon-btn bg-[#1a1a1a] border border-[#333] rounded-lg py-1.5 px-1 text-[11px] font-medium hover:border-neon-lime hover:text-neon-lime transition-colors truncate"
                    >
                      {s.name}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {sounds.length === 0 && (
              <p className="text-xs opacity-40 text-center py-4">
                No sounds loaded
              </p>
            )}
          </div>
        </Card>

        {/* --- SENSORS PANEL --- */}
        <Card title="Sensors" accentColor="text-neon-orange">
          <div className="flex flex-col gap-2">
            <h3 className="text-xs font-bold uppercase tracking-wider opacity-50">
              Proximity
            </h3>
            <ProximityBar
              label="L"
              value={sensors.proximity_left}
              color="#00ffff"
            />
            <ProximityBar
              label="R"
              value={sensors.proximity_right}
              color="#ff00ff"
            />
            <ProximityBar
              label="Rear"
              value={sensors.proximity_rear}
              color="#00ff00"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div
              className={`rounded-xl p-2 text-center text-xs font-bold border ${
                sensors.picked_up
                  ? "bg-yellow-900/40 border-yellow-600 text-yellow-300"
                  : "bg-[#1a1a1a] border-[#333] opacity-40"
              }`}
            >
              Picked Up
            </div>
            <div
              className={`rounded-xl p-2 text-center text-xs font-bold border ${
                sensors.clap_detected
                  ? "bg-orange-900/40 border-orange-600 text-orange-300"
                  : "bg-[#1a1a1a] border-[#333] opacity-40"
              }`}
            >
              Clap
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <h3 className="text-xs font-bold uppercase tracking-wider opacity-50">
              Head
            </h3>
            <div className="grid grid-cols-2 gap-1 font-mono text-xs">
              <span className="opacity-60">
                Pitch:{" "}
                <span className="text-neon-orange">{sensors.head_pitch}</span>
              </span>
              <span className="opacity-60">
                Yaw:{" "}
                <span className="text-neon-orange">{sensors.head_yaw}</span>
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <h3 className="text-xs font-bold uppercase tracking-wider opacity-50">
              Wheels
            </h3>
            <div className="grid grid-cols-2 gap-1 font-mono text-xs">
              <span className="opacity-60">
                L:{" "}
                <span className="text-neon-cyan">
                  {sensors.wheel_distance_left}
                </span>
              </span>
              <span className="opacity-60">
                R:{" "}
                <span className="text-neon-cyan">
                  {sensors.wheel_distance_right}
                </span>
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <h3 className="text-xs font-bold uppercase tracking-wider opacity-50">
              Orientation
            </h3>
            <div className="grid grid-cols-3 gap-1 font-mono text-xs">
              <span className="opacity-60">
                X: <span className="text-neon-lime">{sensors.tilt_x}</span>
              </span>
              <span className="opacity-60">
                Y: <span className="text-neon-lime">{sensors.tilt_y}</span>
              </span>
              <span className="opacity-60">
                Z: <span className="text-neon-lime">{sensors.tilt_z}</span>
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* === CHAT PANEL === */}
      <Card
        title="Chat with Dash"
        accentColor="text-neon-yellow"
        className="min-h-[200px]"
      >
        <div className="flex-1 overflow-y-auto max-h-[250px] flex flex-col gap-2 pr-1">
          {chatHistory.length === 0 && (
            <p className="text-xs opacity-30 text-center py-8">
              Say something to Dash! Try &quot;Move forward and flash your
              lights&quot;
            </p>
          )}
          {chatHistory.map((msg, i) => (
            <div
              key={i}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${
                  msg.role === "user"
                    ? "bg-cyan-900/40 text-cyan-100 border border-cyan-800"
                    : "bg-[#1a1a1a] text-gray-200 border border-[#333]"
                }`}
              >
                <p>{msg.content}</p>
                {msg.actions && msg.actions.length > 0 && (
                  <div className="mt-2 flex flex-col gap-1">
                    {msg.actions.map((action, j) => (
                      <span
                        key={j}
                        className="inline-block bg-purple-900/40 text-purple-300 border border-purple-800 rounded-lg px-2 py-0.5 text-xs"
                      >
                        {"> "}
                        {action}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {chatLoading && (
            <div className="flex justify-start">
              <div className="bg-[#1a1a1a] border border-[#333] rounded-2xl px-4 py-2 text-sm text-gray-400">
                Thinking...
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="flex gap-2 mt-2">
          <input
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleChat()}
            placeholder="Tell Dash what to do..."
            className="flex-1 bg-[#1a1a1a] border border-[#333] rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-neon-yellow transition-colors"
          />
          <button
            onClick={handleChat}
            disabled={chatLoading || !chatInput.trim()}
            className="neon-btn px-5 py-2.5 bg-yellow-900/40 text-neon-yellow border border-yellow-700 rounded-xl text-sm font-bold disabled:opacity-30"
          >
            Send
          </button>
        </div>
      </Card>
    </div>
  );
}
