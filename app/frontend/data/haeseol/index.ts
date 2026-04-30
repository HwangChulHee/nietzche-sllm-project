import { ep1Screen2Haeseol } from "./ep1_screen2_summit";
import { ep1Screen3Haeseol } from "./ep1_screen3_forest";
import { ep1Screen4Haeseol } from "./ep1_screen4_road";
import { ep2Screen1Haeseol } from "./ep2_screen1_market";
import { ep2Screen2Haeseol } from "./ep2_screen2_uebermensch";
import { ep2Screen3Haeseol } from "./ep2_screen3_clown_fall";
import type { HaeseolEntry } from "./types";

const REGISTRY: Record<string, HaeseolEntry> = {
  [ep1Screen2Haeseol.screenId]: ep1Screen2Haeseol,
  [ep1Screen3Haeseol.screenId]: ep1Screen3Haeseol,
  [ep1Screen4Haeseol.screenId]: ep1Screen4Haeseol,
  [ep2Screen1Haeseol.screenId]: ep2Screen1Haeseol,
  [ep2Screen2Haeseol.screenId]: ep2Screen2Haeseol,
  [ep2Screen3Haeseol.screenId]: ep2Screen3Haeseol,
};

export function getHaeseolByScreenId(screenId: string): HaeseolEntry | null {
  return REGISTRY[screenId] ?? null;
}
