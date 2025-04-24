import { useState, useEffect } from "react";
import Vapi from "@vapi-ai/web";

const vapi = new Vapi(import.meta.env.VITE_VAPI_API_KEY);
const assistantId = import.meta.env.VITE_ASSISTANT_ID;

function App() {
  const [started, setStarted] = useState(false);
  const [assistantSpeaking, setAssistantSpeaking] = useState(false);
  const [volumeLevel, setVolumeLevel] = useState(0);

  useEffect(() => {
    vapi
      .on("call-start", () => {
        setStarted(true);
      })
      .on("call-end", () => {
        setStarted(false);
      })
      .on("speech-start", () => {
        setAssistantSpeaking(true);
      })
      .on("speech-end", () => {
        setAssistantSpeaking(false);
      })
      .on("volume-level", (level) => {
        setVolumeLevel(level);
      });
  }, []);

  const startAssistant = async () => {
    await vapi.start(assistantId);
  };

  const stopAssistant = () => {
    vapi.stop();
  };

  return (
    <div>
      <div className="agent-info">
        <p><strong>Want to talk to somebody?</strong></p>
        <p>Try our AI voice assistant:</p>
        <p><strong>📞 +1 240-782-8375</strong></p>
        <p style={{ color: "gray", fontStyle: "italic" }}>Web call feature now live</p>
      </div>

      {/* Call Buttons */}
      <div className="vapi-buttons">
        <button id="call-btn" onClick={startAssistant} disabled={started}>📞 Call Agent</button>
        <button id="hangup-btn" onClick={stopAssistant} disabled={!started}>❌ Hang Up</button>
      </div>

      {/* Speaking indicator */}
      {started && (
        <div className="agent-status">
          <p>{assistantSpeaking ? "🗣️ Agent Speaking..." : "🤔 Waiting for agent..."}</p>
        </div>
      )}

      {/* Volume bars */}
      {started && (
        <div className="volume-bars">
          {Array.from({ length: 10 }).map((_, idx) => (
            <div
              key={idx}
              className={`bar ${idx / 10 < volumeLevel ? "active" : ""}`}
            ></div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;
