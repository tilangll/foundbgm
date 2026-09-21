const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

class Element {
  constructor() {
    this.dataset = {};
    this.style = {};
    this.attributes = {};
    this.listeners = {};
    this.children = [];
    this.classes = new Set();
    this.playCount = 0;
    this.paused = true;
    this.classList = {
      add: (name) => this.classes.add(name),
      remove: (name) => this.classes.delete(name),
    };
  }

  addEventListener(name, listener) { this.listeners[name] = listener; }
  getAttribute(name) { return this.attributes[name] ?? null; }
  removeEventListener(name, listener) {
    if (this.listeners[name] === listener) delete this.listeners[name];
  }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; this[name] = ""; }
  play() { this.playCount += 1; this.paused = false; return Promise.resolve(); }
  pause() { this.paused = true; }
  load() {}
  querySelector(selector) {
    const className = selector.slice(1);
    const pending = [...this.children];
    while (pending.length) {
      const child = pending.shift();
      if (child.className === className) return child;
      pending.push(...child.children);
    }
    return null;
  }
  append(...children) { this.children.push(...children); }
  prepend(...children) { this.children.unshift(...children); }
  blur() {}
}

async function main() {
  const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
  const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
  assert.ok(script, "inline script exists");

  const elements = new Map();
  for (const selector of [
    ".memory-page", "#scene-image", "#lamp-control", "#lamp-image",
    "#state-announcement", "#mode-announcement", "#upload-announcement", "#music-announcement", "#match-error", "#music-retry",
    "#cassette-dock", "#dock-handle", "#upload-tile", "#cassette-upload", "#cassette-list",
    "#tape-transition-video", "#scene-loading", "#music-audio", "#reading-audio",
  ]) elements.set(selector, new Element());
  elements.get(".memory-page").dataset = { mode: "day", playerState: "closed" };
  elements.get("#cassette-dock").dataset = { pinned: "false" };
  elements.get("#tape-transition-video").hidden = true;
  elements.get("#scene-loading").hidden = true;
  elements.get("#match-error").hidden = true;
  elements.get("#match-error").textContent = "读带失败，可重新上传磁带试试";
  elements.get("#reading-audio").attributes.src = "./audio/tape-reading-loop.mp3";

  const events = [];
  const fetchCalls = [];
  const pendingLoadingTimers = [];
  const fetch = async (url, options) => {
    fetchCalls.push({ url, options });
    return { ok: true, json: async () => ({ audio_url: "https://example.com/from-yishun.mp3" }) };
  };
  const window = {
    addEventListener() {},
    dispatchEvent: (event) => events.push(event),
    matchMedia: () => ({ matches: false }),
  };
  class Image {
    async decode() { assert.ok(this.src); }
  }
  class CustomEvent {
    constructor(type, options) { this.type = type; this.detail = options.detail; }
  }

  vm.runInNewContext(script, {
    console,
    window,
    document: {
      querySelector: (selector) => elements.get(selector),
      createElement: () => new Element(),
      addEventListener() {},
    },
    Image,
    CustomEvent,
    URL: { createObjectURL: () => "blob:uploaded-image", revokeObjectURL() {} },
    URLSearchParams,
    location: { search: "" },
    AbortController,
    fetch,
    setTimeout: (resolve, delay) => {
      if (delay === 1400) pendingLoadingTimers.push(resolve);
      else queueMicrotask(resolve);
    },
  });

  async function finishLoading() {
    assert.equal(pendingLoadingTimers.length, 1, "one reading animation is waiting to complete");
    pendingLoadingTimers.shift()();
    await new Promise(setImmediate);
  }

  const api = window.MemoryTape;
  assert.ok(fs.statSync(path.join(__dirname, "audio/tape-reading-loop.mp3")).size > 0);
  for (const [cassette, track] of Object.entries({
    "cloud.png": "windswept.mp3",
    "qiuqiu.png": "carefree.mp3",
    "grass.png": "sunshine.mp3",
    "afternoon.png": "bossa-antigua.mp3",
  })) {
    assert.ok(fs.statSync(path.join(__dirname, "audio", track)).size > 0, `${track} is stored locally`);
    assert.ok(html.includes(`["${cassette}", "./audio/${track}"]`), `${cassette} uses its local track`);
  }
  assert.ok(fs.statSync(path.join(__dirname, "video/night-transition-insert2-v2-approach-fast.mp4")).size > 0);
  assert.ok(fs.statSync(path.join(__dirname, "assets/video-playing.mp4")).size > 0);
  assert.ok(html.includes('playsinline preload="auto"'));
  assert.ok(!html.includes('playsinline muted'), "the transition keeps its original soundtrack");
  assert.ok(html.includes('height: max(100dvh, 56.25vw)'), "the scene has a fixed 16:9 display box");
  assert.ok(fs.readFileSync(path.join(__dirname, "assets/video-playing.mp4")).includes(Buffer.from("mp4a")), "day video contains audio");
  assert.ok(fs.readFileSync(path.join(__dirname, "video/night-transition-insert2-v2-approach-fast.mp4")).includes(Buffer.from("mp4a")), "night video contains synchronized audio");
  assert.ok(!html.includes("scene-transition-cover"), "the day video plays without a misaligned cover");
  assert.equal((html.match(/<span style="--index: \d">[Loading.]<\/span>/g) || []).length, 9, "Loading.. has individually animated characters");
  assert.ok(html.includes('.memory-page[data-mode="night"] .scene-loading { top: 23.7%; }'));
  assert.equal(elements.get("#reading-audio").volume, 0.5);
  const cassetteList = elements.get("#cassette-list");
  assert.deepEqual(
    cassetteList.children.map((card) => card.children[0].children[0].src),
    ["./assets/cloud.png", "./assets/qiuqiu.png", "./assets/grass.png", "./assets/afternoon.png"],
  );
  const inlineMask = html.match(/--cassette-photo-mask: url\("data:image\/png;base64,([^"]+)"\)/)?.[1];
  assert.ok(inlineMask, "cassette photo mask is embedded for file:// previews");
  assert.deepEqual(Buffer.from(inlineMask, "base64"), fs.readFileSync(path.join(__dirname, "assets/Mask group.png")));
  assert.ok(html.includes("width: 82.53%"));
  const fileInput = elements.get("#cassette-upload");
  assert.ok(html.includes(".cassette-takeout-empty { display: block; width: 100%; height: 100%; object-fit: contain; opacity: 0.6; }"));
  assert.ok(html.includes('.memory-page[data-mode="night"] .cassette-night { opacity: 1; }'));
  assert.ok(html.includes(".cassette-picture--preset img"));
  assert.equal(api.getMode(), "day");
  assert.equal(api.getState(), "closed");
  assert.equal(Object.keys(api.nightStates).length, 4);
  await api.setState("open");
  assert.equal(elements.get("#scene-image").src, "./assets/day-open.png");

  await api.setMode("night", { animate: true });
  assert.equal(api.getMode(), "night");
  assert.equal(api.getState(), "open");
  assert.equal(elements.get("#scene-image").src, "./assets/night-close.png?v=2");
  assert.equal(elements.get("#lamp-image").src, "./assets/night-lamp.png");
  assert.equal(elements.get(".memory-page").dataset.mode, "night");
  assert.equal(elements.get("#tape-transition-video").src, "./video/night-transition-insert2-v2-approach-fast.mp4");
  assert.equal(events.filter((event) => event.type === "lamppull").length, 1);
  assert.equal(elements.get("#lamp-control").classes.has("is-pulled"), false);

  await api.setMode("day");
  assert.equal(api.getMode(), "day");
  assert.equal(api.getState(), "open");
  assert.equal(elements.get("#scene-image").src, "./assets/day-open.png");
  assert.equal(elements.get("#lamp-image").src, "./assets/lamp.png");
  assert.equal(elements.get("#tape-transition-video").src, "./assets/video-playing.mp4?v=day-restore");
  assert.equal(events.filter((event) => event.type === "modechange").length, 2);

  await api.setState("closed");
  let finishTransition;
  api.setTapeTransition(() => new Promise((resolve) => { finishTransition = resolve; }));
  const cloudSelect = cassetteList.children[0].children[0];
  cloudSelect.listeners.click();
  assert.equal(api.getState(), "closed", "play waits for the future video transition");
  assert.equal(events.filter((event) => event.type === "cassetteplayrequest").length, 1);
  assert.equal(cassetteList.children[0].classes.has("is-playing"), true);
  finishTransition();
  await new Promise(setImmediate);
  assert.equal(api.getState(), "playing");
  assert.equal(elements.get("#scene-image").src, "./assets/day-play.png");
  assert.equal(elements.get("#music-audio").src, "./audio/windswept.mp3", "the first preset plays its bundled track");

  api.setTapeTransition(null);
  api.setPresetTracks({ "qiuqiu.png": "./assets/qiuqiu.mp3" });
  await api.setState("closed");
  const qiuqiuSelect = cassetteList.children[1].children[0];
  qiuqiuSelect.listeners.click();
  assert.equal(elements.get("#tape-transition-video").src, "./assets/video-playing.mp4?v=day-restore");
  assert.equal(elements.get("#tape-transition-video").muted, false, "day transition is unmuted");
  assert.equal(elements.get("#tape-transition-video").volume, 1);
  assert.equal(qiuqiuSelect.children[1].children[0].src, "./assets/night-tape-template.png");
  assert.equal(qiuqiuSelect.children[1].children[1].children[0].src, "./assets/qiuqiu.png");
  assert.equal(qiuqiuSelect.children[2].children[0].src, "./assets/tape（empty）.png");
  assert.equal(qiuqiuSelect.children[2].children[1].src, "./assets/night-tape-template.png");
  assert.equal(qiuqiuSelect.children[2].children[2].textContent, "Take-out");
  assert.ok(html.includes(".cassette-takeout-label {"));
  assert.ok(html.includes("color: #fff;"));
  assert.equal(qiuqiuSelect.attributes["aria-label"], "取出磁带：球球磁带");
  assert.equal(elements.get("#tape-transition-video").hidden, false);
  assert.equal(api.getState(), "closed", "the scene waits for the video to end");
  elements.get("#tape-transition-video").listeners.ended();
  await new Promise(setImmediate);
  assert.equal(api.getState(), "playing");
  assert.equal(elements.get("#tape-transition-video").hidden, true);
  assert.equal(elements.get("#music-audio").src, "./assets/qiuqiu.mp3");
  assert.equal(elements.get("#music-audio").playCount, 2);
  assert.equal(cloudSelect.attributes["aria-pressed"], "false");
  assert.equal(cloudSelect.attributes["aria-label"], "播放磁带：云朵磁带");
  assert.equal(qiuqiuSelect.attributes["aria-pressed"], "true");
  assert.equal(events.filter((event) => event.type === "cassetteplayrequest").length, 2);

  let finishMatch;
  let matchCalls = 0;
  api.setMusicMatcher(() => {
    matchCalls += 1;
    return new Promise((resolve) => { finishMatch = resolve; });
  });
  await api.setState("closed");
  fileInput.files = [{ type: "image/png", name: "uploaded.png" }];
  fileInput.listeners.change();
  const uploaded = cassetteList.children[0];
  const uploadedSelect = uploaded.children[0];
  assert.equal(uploadedSelect.className, "cassette-select");
  assert.equal(uploadedSelect.children[0].src, "./assets/tape（empty）.png");
  assert.equal(uploadedSelect.children[1].children[0].src, "blob:uploaded-image");
  assert.equal(uploadedSelect.children[2].className, "cassette-night");
  assert.equal(uploadedSelect.children[2].children[0].src, "./assets/night-tape-template.png");
  assert.equal(uploadedSelect.children[2].children[1].children[0].src, "blob:uploaded-image");
  assert.equal(uploadedSelect.children[3].className, "cassette-takeout");
  assert.equal(uploadedSelect.children[3].children[0].src, "./assets/tape（empty）.png");
  assert.equal(uploadedSelect.children[3].children[1].src, "./assets/night-tape-template.png");
  assert.equal(uploadedSelect.children[3].children[2].textContent, "Take-out");
  assert.equal(uploaded.children[1].className, "cassette-remove");
  assert.equal(uploadedSelect.attributes["aria-pressed"], "true", "upload starts playback without a second click");
  assert.equal(elements.get("#tape-transition-video").hidden, false, "upload starts the insertion video");
  assert.equal(events.filter((event) => event.type === "musicmatchstart").length, 1);
  assert.equal(elements.get("#match-error").hidden, true);
  await new Promise(setImmediate);
  assert.equal(matchCalls, 1, "music matching begins before the video ends");
  assert.equal(elements.get("#reading-audio").playCount, 0, "reading waits for the insertion video");
  assert.equal(elements.get("#reading-audio").paused, true);
  assert.equal(elements.get("#scene-loading").hidden, true, "Loading stays hidden during insertion");
  elements.get("#tape-transition-video").listeners.ended();
  await new Promise(setImmediate);
  assert.equal(api.getState(), "playing");
  assert.equal(elements.get("#reading-audio").playCount, 1);
  assert.equal(elements.get("#reading-audio").paused, false, "reading loops while matching");
  assert.equal(elements.get("#scene-loading").hidden, false, "Loading appears with the reading sound");
  finishMatch({ audio_url: "https://example.com/matched.mp3", name: "Matched" });
  await new Promise(setImmediate);
  assert.equal(elements.get("#scene-loading").hidden, false, "Loading completes its typing animation before music starts");
  await finishLoading();
  assert.equal(elements.get("#reading-audio").paused, true);
  assert.equal(elements.get("#scene-loading").hidden, true, "Loading stops when matching succeeds");
  assert.equal(elements.get("#music-audio").src, "https://example.com/matched.mp3");
  assert.equal(elements.get("#music-audio").playCount, 3);
  assert.equal(uploadedSelect.attributes["aria-pressed"], "true");
  assert.equal(uploadedSelect.attributes["aria-label"], "取出磁带：uploaded.png");
  assert.equal(events.filter((event) => event.type === "cassetteplayrequest").length, 3);
  assert.equal(events.filter((event) => event.type === "musicmatchend").length, 1);
  api.setMusicMatcher(null);
  uploadedSelect.listeners.click();
  await new Promise(setImmediate);
  assert.equal(api.getState(), "closed", "Take-out returns the player to its empty state");
  assert.equal(uploadedSelect.attributes["aria-label"], "播放磁带：uploaded.png");
  uploadedSelect.listeners.click();
  await new Promise(setImmediate);
  elements.get("#tape-transition-video").listeners.ended();
  await new Promise(setImmediate);
  assert.equal(elements.get("#scene-loading").hidden, false, "a fast day match still shows Loading after the video");
  await finishLoading();
  assert.equal(fetchCalls.length, 1);
  assert.equal(fetchCalls[0].url, "/api/match");
  assert.equal(fetchCalls[0].options.body.name, "uploaded.png");
  assert.equal(elements.get("#music-audio").src, "https://example.com/from-yishun.mp3");
  await api.setState("closed");
  await api.setMode("night");
  assert.equal(elements.get("#scene-image").src, "./assets/night-close.png?v=2");
  await api.setState("tapeReady");
  assert.equal(elements.get("#scene-image").src, "./assets/night-insert.png?v=2");
  cloudSelect.listeners.click();
  assert.equal(elements.get("#tape-transition-video").src, "./video/night-transition-insert2-v2-approach-fast.mp4");
  assert.equal(elements.get("#tape-transition-video").muted, false, "night transition is unmuted");
  assert.equal(elements.get("#tape-transition-video").hidden, false, "night cassette click reveals the transition video");
  assert.equal(elements.get("#tape-transition-video").playCount, 4, "night cassette click starts video playback");
  assert.equal(api.getState(), "tapeReady", "night scene waits for the night transition video");
  elements.get("#tape-transition-video").listeners.ended();
  await new Promise(setImmediate);
  assert.equal(api.getState(), "playing");
  assert.equal(elements.get("#scene-image").src, "./assets/night-play.png?v=2");
  cloudSelect.listeners.click();
  await new Promise(setImmediate);
  assert.equal(api.getState(), "closed");
  assert.equal(cloudSelect.attributes["aria-pressed"], "false");
  assert.equal(cloudSelect.attributes["aria-label"], "播放磁带：云朵磁带");
  assert.equal(events.filter((event) => event.type === "cassetteeject").length, 2);

  let finishNightMatch;
  api.setMusicMatcher(() => new Promise((resolve) => { finishNightMatch = resolve; }));
  const readingCountBeforeNight = elements.get("#reading-audio").playCount;
  const uploadTile = elements.get("#upload-tile");
  uploadTile.listeners.drop({
    preventDefault() {},
    dataTransfer: { files: [
      { type: "image/png", name: "first.png" },
      { type: "image/jpeg", name: "last.jpg" },
    ] },
  });
  assert.equal(cassetteList.children[0].attributes["aria-label"], "last.jpg");
  assert.equal(cassetteList.children[1].attributes["aria-label"], "first.png");
  assert.equal(cassetteList.children[0].children[0].attributes["aria-pressed"], "true", "the topmost new tape autoplays");
  assert.equal(cassetteList.children[1].children[0].attributes["aria-pressed"], "false");
  assert.equal(elements.get("#tape-transition-video").playCount, 5);
  await new Promise(setImmediate);
  assert.equal(typeof finishNightMatch, "function", "night upload starts matching before the video ends");
  assert.equal(elements.get("#reading-audio").playCount, readingCountBeforeNight);
  assert.equal(elements.get("#scene-loading").hidden, true);
  elements.get("#tape-transition-video").listeners.ended();
  await new Promise(setImmediate);
  assert.equal(elements.get("#reading-audio").playCount, readingCountBeforeNight + 1);
  assert.equal(elements.get("#reading-audio").paused, false);
  assert.equal(elements.get("#scene-loading").hidden, false, "night reading uses the same Loading indicator");
  finishNightMatch({ audio_url: "https://example.com/night-match.mp3" });
  await new Promise(setImmediate);
  assert.equal(elements.get("#scene-loading").hidden, false, "night Loading remains visible long enough to finish typing");
  await finishLoading();
  assert.equal(elements.get("#reading-audio").paused, true);
  assert.equal(elements.get("#scene-loading").hidden, true);
  api.setMusicMatcher(null);

  const switching = api.setMode("day", { animate: true });
  fileInput.files = [{ type: "image/png", name: "during-switch.png" }];
  fileInput.listeners.change();
  const queuedSelect = cassetteList.children[0].children[0];
  assert.equal(queuedSelect.attributes["aria-pressed"], "false", "upload waits for the mode change");
  await switching;
  assert.equal(queuedSelect.attributes["aria-pressed"], "true", "upload starts after the mode change");
  assert.equal(elements.get("#tape-transition-video").src, "./assets/video-playing.mp4?v=day-restore");
  await new Promise(setImmediate);
  const readingCountBeforeFastMatch = elements.get("#reading-audio").playCount;
  elements.get("#tape-transition-video").listeners.ended();
  await new Promise(setImmediate);
  assert.equal(api.getState(), "playing");
  assert.equal(elements.get("#reading-audio").playCount, readingCountBeforeFastMatch + 1, "reading starts after the insertion video");
  assert.equal(elements.get("#scene-loading").hidden, false, "a fast match still shows Loading");
  await finishLoading();
  assert.equal(elements.get("#scene-loading").hidden, true);

  const matchErrorsBefore = events.filter((event) => event.type === "musicmatcherror").length;
  let failMatch;
  api.setMusicMatcher(() => new Promise((_, reject) => { failMatch = reject; }));
  fileInput.files = [{ type: "image/png", name: "failed.png" }];
  fileInput.listeners.change();
  assert.equal(elements.get("#match-error").hidden, true);
  await new Promise(setImmediate);
  assert.equal(typeof failMatch, "function");
  assert.equal(elements.get("#reading-audio").paused, true);
  const readingCountBeforeFailure = elements.get("#reading-audio").playCount;
  elements.get("#tape-transition-video").listeners.ended();
  await new Promise(setImmediate);
  assert.equal(elements.get("#reading-audio").playCount, readingCountBeforeFailure + 1);
  assert.equal(elements.get("#reading-audio").paused, false);
  assert.equal(elements.get("#scene-loading").hidden, false);
  failMatch(new Error("matching unavailable"));
  await new Promise(setImmediate);
  assert.equal(elements.get("#scene-loading").hidden, false, "a fast failure still completes Loading");
  await finishLoading();
  assert.equal(elements.get("#reading-audio").paused, true, "reading sound stops when matching fails");
  assert.equal(elements.get("#scene-loading").hidden, true, "Loading stops when matching fails");
  assert.equal(elements.get("#match-error").hidden, false, "matching failure is visible");
  assert.equal(elements.get("#match-error").textContent, "读带失败，可重新上传磁带试试");
  assert.equal(events.filter((event) => event.type === "musicmatcherror").length, matchErrorsBefore + 1);

  api.setMusicMatcher(() => null);
  const readingPlay = elements.get("#reading-audio").play;
  elements.get("#reading-audio").play = () => Promise.reject(new Error("autoplay blocked"));
  fileInput.files = [{ type: "image/png", name: "no-track.png" }];
  fileInput.listeners.change();
  assert.equal(elements.get("#match-error").hidden, true, "a new upload clears the previous error");
  elements.get("#tape-transition-video").listeners.ended();
  await new Promise(setImmediate);
  assert.equal(elements.get("#scene-loading").hidden, false, "Loading is visible even if reading audio cannot autoplay");
  await finishLoading();
  elements.get("#reading-audio").play = readingPlay;
  assert.equal(elements.get("#reading-audio").paused, true);
  assert.equal(elements.get("#match-error").hidden, false, "an empty match also shows the retry message");
  assert.equal(events.filter((event) => event.type === "musicmatcherror").length, matchErrorsBefore + 2);

  api.setReadingAudio("./audio/another-reading.mp3");
  assert.equal(elements.get("#reading-audio").src, "./audio/another-reading.mp3");
  console.log("Cassette video, auto-upload, Take-out, music matching, reading loop, and day/night switching: OK");
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
