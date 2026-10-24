const SPEAK_KEY = "bv-speak-cues";

export const speakSetting = {
  get: () => localStorage.getItem(SPEAK_KEY) !== "off",
  set: (on) => localStorage.setItem(SPEAK_KEY, on ? "on" : "off"),
};

export function unlockSpeech() {
  try {
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(""));
  } catch {
    /* speech not supported */
  }
}

export function speak(text) {
  try {
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
    return true;
  } catch {
    return false;
  }
}
