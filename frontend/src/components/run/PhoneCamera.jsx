import { useEffect } from "react";
import { usePhoneCamera } from "@/hooks/usePhoneCamera";

export default function PhoneCamera({ attemptId, streamKey, running, glassesQuiet, motionRef, announce }) {
  const cam = usePhoneCamera({ attemptId, streamKey, motionRef, onError: announce });
  const { on, stop } = cam;

  useEffect(() => {
    if (!running && on) stop();
  }, [running, on, stop]);

  if (on) {
    return (
      <section className="bv-run-section" aria-label="Phone camera" data-testid="phone-camera">
        <video ref={cam.videoRef} muted playsInline autoPlay className="bv-cam-preview" aria-label="Phone camera preview" data-testid="phone-camera-preview" />
        <button type="button" className="bv-btn bv-run-btn" onClick={() => { stop(); announce("Phone camera stopped"); }} data-testid="stop-phone-camera-button">
          Stop phone camera
        </button>
      </section>
    );
  }
  if (!running || !glassesQuiet) return null;
  return (
    <section className="bv-run-section" aria-label="Phone camera">
      <p>The glasses aren't sending video.</p>
      <button type="button" className="bv-btn bv-run-btn" onClick={cam.start} data-testid="use-phone-camera-button">Use phone camera</button>
    </section>
  );
}
