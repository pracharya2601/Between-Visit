import { useCallback, useEffect, useRef, useState } from "react";
import { API } from "@/lib/api";

function postFrame(video, canvas, url, streamKey) {
  if (!video?.videoWidth) return;
  const w = Math.min(640, video.videoWidth);
  canvas.width = w;
  canvas.height = Math.round((video.videoHeight * w) / video.videoWidth);
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
  canvas.toBlob((blob) => {
    if (!blob) return;
    fetch(url(), { method: "POST", headers: { "X-Stream-Key": streamKey, "Content-Type": "image/jpeg" }, body: blob }).catch(() => {});
  }, "image/jpeg", 0.7);
}

export function usePhoneCamera({ attemptId, streamKey, motionRef, onError }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [on, setOn] = useState(false);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setOn(false);
  }, []);

  const start = async () => {
    try {
      streamRef.current = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
      setOn(true);
    } catch {
      onError("Camera not available");
    }
  };

  useEffect(() => {
    if (!on) return;
    const video = videoRef.current;
    video.srcObject = streamRef.current;
    video.play().catch(() => {});
    const canvas = document.createElement("canvas");
    const url = () => {
      const q = new URLSearchParams();
      const { heading, steps } = motionRef.current;
      if (heading != null) q.set("heading", heading);
      q.set("steps", steps);
      return `${API}/attempts/${attemptId}/frame?${q}`;
    };
    const t = setInterval(() => postFrame(video, canvas, url, streamKey), 1000);
    return () => { clearInterval(t); video.srcObject = null; };
  }, [on, attemptId, streamKey, motionRef]);

  useEffect(() => stop, [stop]);
  return { on, start, stop, videoRef };
}
