// Home-kit [primary, secondary] colors per club, for the jersey icons in the
// starting-XI pitch view and the "plays a similar game" cards. Static and
// small enough to hardcode rather than fetch — these change once a season
// at most, and only for promoted/relegated clubs.
const KITS = {
  ARS: ["#ef3340", "#0b2340"],
  AVL: ["#7c2140", "#8ec6ec"],
  BHA: ["#1f6fd0", "#0d2f5c"],
  BOU: ["#c8102e", "#141414"],
  BRE: ["#d6182b", "#f0d24a"],
  CHE: ["#2a5cb8", "#0d1f47"],
  COV: ["#5fb2e8", "#1a3a5c"],
  CRY: ["#2a4d9b", "#c8102e"],
  EVE: ["#28418a", "#111a3a"],
  FUL: ["#e2e5ef", "#161616"],
  HUL: ["#f5a623", "#111111"],
  IPS: ["#1e5cb3", "#0c2a5c"],
  LEE: ["#f5f5f5", "#1c3a6e"],
  LIV: ["#c8102e", "#5d0a18"],
  MCI: ["#7fb3dd", "#0b2c52"],
  MUN: ["#dc1f26", "#0a0a0a"],
  NEW: ["#3b3b3b", "#dfe3ee"],
  NFO: ["#d8232a", "#4a0d10"],
  SUN: ["#e0202b", "#f0f0f0"],
  TOT: ["#dfe3ee", "#131a3a"],
};

const DEFAULT_KIT = ["#75798c", "#292b31"];

export function kitFor(teamShortName) {
  return KITS[teamShortName] || DEFAULT_KIT;
}
