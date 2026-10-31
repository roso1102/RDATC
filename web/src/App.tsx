import { useEffect, useRef, useState } from 'react';
import { RadarView, radarSummary, type RadarReading } from './Radar';
import { Scene3D, type ScenePerson, type SceneView } from './Scene3D';

type IRReading = {
  sequence: number; object_temperature_c: number | null; sensor_temperature_c: number | null;
  source: string; scenario_id: string; generated_at_utc: string;
};
type Detection = {
  status: string; inference_location: string; execution_note: string | null; error: string | null; frame_id: string | null;
  person_count: number | null; inference_ms: number | null; score_threshold: number | null;
  input_width: number | null; input_height: number | null;
  model: { name: string; licence: string } | null;
  detections: { label: string; score: number; box_xyxy: [number, number, number, number] }[];
};
type EdgeDetection = {
  status: string; frame_id: string | null; score: number | null; person: boolean | null;
  infer_ms: number | null; prep_ms: number | null; model: string | null; threshold: number;
};
type Fusion = {
  decision: string; index: number | null; coverage: number; coverage_status: string; disagreement: boolean;
  pending_candidate: string | null; pending_count: number; config: { persist_updates: number };
  contributions: Record<string, { weight: number; evidence: number | null; available: boolean }>;
};
type StationState = {
  mode: string; server_time_utc: string;
  camera: { status: string; available: boolean; url: string | null; error: string | null;
    receive_age_ms: number | null; frame: { frame_id: string; width: number; height: number;
      content: string; node_rssi_dbm: number | null } | null };
  detection: Detection;
  edge_detection: EdgeDetection;
  ir: { scenario: string; hardware_status: string; reading: IRReading | null };
  radar: { status: string; available: boolean; enabled: boolean; address: string | null;
    error: string | null; receive_age_ms: number | null; reading: RadarReading | null };
  profile: { active: string; label: string; version: string; weights_status: string; ir_rule: string | null;
    weights: Record<string, number>; prior_weights?: Record<string, number> };
  assessment: { status: string; reason: string; fusion_enabled: boolean; person_count: number | null;
    decision: string; fusion_index: number | null; coverage: number };
  fusion: Fusion | null;
  recording: { active: boolean; session_id: string | null; events: number; frames: number; error: string | null };
};
type RadarDevice = { name: string; address: string; rssi_dbm: number };
type Frame = { url: string; frameId: string };

const pretty = (value: string) => value.toLowerCase().replaceAll('_', ' ');
const sentence = (value: string) => { const text = pretty(value); return text.charAt(0).toUpperCase() + text.slice(1); };
const number = (value: number | null | undefined, digits = 1) => value == null ? '—' : value.toFixed(digits);
const percent = (value: number | null | undefined) => value == null ? '—' : `${Math.round(value * 100)}%`;

// Headline wording for each fused decision. "Human detected" is the provisional fused result.
const HEADLINES: Record<string, { title: string; tone: string }> = {
  POSSIBLE_PERSON: { title: 'Human detected', tone: 'human' },
  NO_PERSON_INDICATED: { title: 'No human detected', tone: 'clear' },
  NO_PERSON_INDICATED_PARTIAL_COVERAGE: { title: 'No human detected', tone: 'clear' },
  UNCERTAIN: { title: 'Checking…', tone: 'checking' },
  INSUFFICIENT_EVIDENCE: { title: 'Waiting for sensors', tone: 'idle' },
};
// Operator-selected conditions; disaster priors are literature-informed (docs/RESULTS_GUIDE.md section 4).
const CONDITIONS = [['clear', 'Clear'], ['reduced_visibility', 'Low visibility'], ['fire_no_smoke', 'Fire'],
  ['fire_smoke', 'Fire + smoke'], ['flood', 'Flood'], ['earthquake', 'Earthquake']];
const CAMERA_HALF_FOV_DEG = 25;  // Assumed OV7670 lens; the direction estimate is uncalibrated.
const LAST_SEEN_MS = 15000;
const SCENARIOS = [['baseline', 'Baseline'], ['warm_target', 'Warm target'],
  ['hot_background', 'Hot background'], ['unavailable', 'Unavailable']];

export default function App() {
  const [state, setState] = useState<StationState | null>(null);
  const [backendError, setBackendError] = useState('');
  const [actionError, setActionError] = useState('');
  const [busy, setBusy] = useState(false);
  const [cameraUrl, setCameraUrl] = useState('');
  const [devices, setDevices] = useState<RadarDevice[]>([]);
  const [radarAddress, setRadarAddress] = useState('');
  const [frames, setFrames] = useState<Frame[]>([]);
  const [history, setHistory] = useState<number[]>([]);
  const owned = useRef<string[]>([]);
  const [view, setView] = useState<SceneView>('perspective');
  const lastSeen = useRef<{ distanceM: number; bearingDeg: number; rangeKnown: boolean; at: number } | null>(null);

  useEffect(() => {
    let active = true, fetching = false;
    let controller: AbortController | null = null;
    const poll = async () => {
      if (fetching) return;
      fetching = true;
      controller = new AbortController();
      const timeout = window.setTimeout(() => controller?.abort(), 3500);
      try {
        const response = await fetch('/api/state', { signal: controller.signal, cache: 'no-store' });
        if (!response.ok) throw new Error('Backend unavailable');
        const next = await response.json() as StationState;
        if (active) { setState(next); setBackendError(''); }
      } catch {
        if (active) setBackendError('Backend connection lost. Displayed values are no longer live.');
      } finally { fetching = false; window.clearTimeout(timeout); }
    };
    void poll();
    const interval = window.setInterval(() => void poll(), 500);
    return () => { active = false; controller?.abort(); window.clearInterval(interval); };
  }, []);

  useEffect(() => { setCameraUrl(state?.camera.url || ''); }, [state?.camera.url]);
  useEffect(() => { if (state?.radar.address) setRadarAddress(state.radar.address); }, [state?.radar.address]);
  useEffect(() => {
    const value = state?.ir.reading?.object_temperature_c;
    if (value != null && !backendError) setHistory(old => [...old.slice(-59), value]);
  }, [state?.ir.reading?.sequence]);

  // Keep the previous frame underneath while the next one fades in; decode before showing.
  useEffect(() => {
    const controller = new AbortController();
    if (!state?.camera.available || backendError) {
      owned.current.forEach(url => URL.revokeObjectURL(url));
      owned.current = []; setFrames([]);
      return;
    }
    void (async () => {
      try {
        const response = await fetch('/api/camera/frame', { signal: controller.signal, cache: 'no-store' });
        if (!response.ok) throw new Error('Frame unavailable');
        const url = URL.createObjectURL(await response.blob());
        const image = new Image(); image.src = url;
        await image.decode().catch(() => undefined);
        if (controller.signal.aborted) { URL.revokeObjectURL(url); return; }
        owned.current.push(url);
        while (owned.current.length > 2) URL.revokeObjectURL(owned.current.shift()!);
        setFrames(old => [...old.slice(-1), { url, frameId: response.headers.get('X-Frame-Id') || 'unknown frame' }]);
      } catch { /* Keep the last frame; the status chip reports availability. */ }
    })();
    return () => controller.abort();
  }, [state?.camera.frame?.frame_id, state?.camera.available, backendError]);
  useEffect(() => () => owned.current.forEach(url => URL.revokeObjectURL(url)), []);

  async function act(path: string, body?: unknown) {
    setBusy(true); setActionError('');
    try {
      const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(20000) });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Request was rejected');
      return result;
    } catch (error) { setActionError(error instanceof Error ? error.message : 'Request failed'); return null; }
    finally { setBusy(false); }
  }

  const disabled = busy || !state || !!backendError;
  const live = !!state && !backendError;
  const detection = state?.detection;
  const fusion = live ? state.fusion : null;
  const decision = live ? state.assessment.decision || 'INSUFFICIENT_EVIDENCE' : 'OFFLINE';
  const headline = HEADLINES[decision] || { title: backendError ? 'Ground station offline' : 'Connecting…', tone: 'idle' };
  const current = frames[frames.length - 1];
  const testPattern = state?.camera.frame?.content === 'SENSOR_TEST_PATTERN';
  // Draw boxes only on the exact frame they were computed from.
  const boxes = current && detection?.status === 'READY' && detection.frame_id === current.frameId
    && detection.input_width && detection.input_height ? detection : null;
  const edge = live ? state.edge_detection : null;
  const edgeOnFrame = current && edge?.status === 'READY' && edge.frame_id === current.frameId ? edge : null;
  const frameSize = state?.camera.frame;
  const radar = live && state.radar.available ? state.radar.reading : null;
  // Illustrative placement: radar range plus the camera's left/right estimate from the best box.
  const radarRange = radar?.presence
    ? (radar.moving ? radar.moving_distance_cm : radar.stationary_distance_cm) / 100 : null;
  const best = detection?.status === 'READY' && detection.input_width
    ? [...detection.detections].sort((a, b) => b.score - a.score)[0] : undefined;
  const bearing = best && detection?.input_width
    ? ((best.box_xyxy[0] + best.box_xyxy[2]) / 2 / detection.input_width - 0.5) * 2 * CAMERA_HALF_FOV_DEG : 0;
  if (decision === 'POSSIBLE_PERSON') {
    lastSeen.current = { distanceM: radarRange ?? 2.5, bearingDeg: bearing, rangeKnown: radarRange != null, at: Date.now() };
  }
  const seen = lastSeen.current;
  const scenePerson: ScenePerson = decision === 'POSSIBLE_PERSON' && seen ? { state: 'present', ...seen }
    : seen && Date.now() - seen.at < LAST_SEEN_MS ? { state: 'last_seen', ...seen }
    : { state: 'none', distanceM: seen?.distanceM ?? 2.5, bearingDeg: seen?.bearingDeg ?? 0 };
  const cameraEvidence = fusion?.contributions.camera;
  const radarEvidence = fusion?.contributions.radar;
  const ir = state?.ir.reading;
  // Scale to the data, but never tighter than 3 °C so noise does not look like a trend.
  const middle = history.length ? (Math.min(...history) + Math.max(...history)) / 2 : 25;
  const span = Math.max(3, history.length ? Math.max(...history) - Math.min(...history) + 1 : 3);
  const low = middle - span / 2, high = middle + span / 2;
  const spark = history.map((value, index) =>
    `${(index / Math.max(59, history.length - 1) * 300).toFixed(1)},${(56 - (value - low) / (high - low) * 52).toFixed(1)}`);

  return <div className="app">
    <header className="topbar">
      <div className="brand"><span className="logo" aria-hidden="true" /><div><strong>ARES</strong>
        <span>Emergency support ground station</span></div></div>
      <div className="topbar-actions">
        <span className={`chip ${live ? (state.mode === 'MIXED' ? 'ok' : 'warn') : 'bad'}`}>
          <i className="dot" />{!state ? 'Connecting' : backendError ? 'Offline' : state.mode === 'MIXED' ? 'Live' : 'Simulation only'}</span>
        <button className={`record ${state?.recording.active ? 'on' : ''}`} disabled={disabled}
          onClick={() => void act(`/api/recording/${state?.recording.active ? 'stop' : 'start'}`)}>
          <i />{state?.recording.active ? `Recording · ${state.recording.frames}` : 'Record'}</button>
      </div>
    </header>
    {(backendError || actionError) && <div role="alert" className="alert">{backendError || actionError}</div>}

    <section className={`hero ${headline.tone}`} aria-live="polite">
      <div className="hero-status">
        <span className="hero-dot" aria-hidden="true" />
        <div>
          <h1 key={headline.title}>{headline.title}</h1>
          <p>{decision === 'POSSIBLE_PERSON'
            ? `${cameraEvidence?.available && cameraEvidence.evidence ? 'Seen by camera' : 'Sensed by radar'}${
              radarEvidence?.available && radarEvidence.evidence && cameraEvidence?.evidence ? ' and radar' : ''} · provisional fusion`
            : decision === 'NO_PERSON_INDICATED_PARTIAL_COVERAGE' ? 'Only part of the sensor set is reporting'
            : decision === 'UNCERTAIN' ? 'Evidence is mixed; waiting for it to settle'
            : decision === 'NO_PERSON_INDICATED' ? (radarEvidence?.evidence ? 'Radar senses something the camera does not see'
              : cameraEvidence?.evidence ? 'Weak camera signal only' : 'Camera and radar both quiet')
            : 'No current camera or radar evidence'}</p>
          <div className="hero-tags">
            {fusion && fusion.coverage_status !== 'FULL' && fusion.index != null && <span className="chip warn">Partial coverage · {percent(fusion.coverage)}</span>}
            {fusion?.disagreement && <span className="chip warn">Sensors disagree</span>}
            {fusion?.pending_candidate && fusion.pending_count < fusion.config.persist_updates &&
              <span className="chip">Confirming {pretty(fusion.pending_candidate)}…</span>}
          </div>
        </div>
      </div>
      <div className="hero-side">
        <div className="meter"><span>Camera</span><div className="bar"><div style={{ width: `${(cameraEvidence?.evidence ?? 0) * 100}%` }} /></div>
          <b>{cameraEvidence?.available ? percent(cameraEvidence.evidence) : 'off'}</b></div>
        <div className="meter"><span>Radar</span><div className="bar radar-bar"><div style={{ width: `${(radarEvidence?.evidence ?? 0) * 100}%` }} /></div>
          <b>{radarEvidence?.available ? (radarEvidence.evidence ? 'present' : 'none') : 'off'}</b></div>
        <div className="conditions" role="radiogroup" aria-label="Operator-selected condition">
          {CONDITIONS.map(([value, label]) =>
            <button key={value} role="radio" aria-checked={state?.profile.active === value} disabled={disabled}
              className={state?.profile.active === value ? 'active' : ''}
              onClick={() => state?.profile.active !== value && void act('/api/config/profile', { profile: value })}>{label}</button>)}
        </div>
        {state?.profile && <p className="weights-line">
          Camera {percent(state.profile.weights.camera)} · Radar {percent(state.profile.weights.radar)}
          {(state.profile.prior_weights?.ir ?? 0) > 0 && <> · IR {percent(state.profile.prior_weights?.ir)} prior, applied 0 (simulated)</>}
          <span>{state.profile.weights_status === 'LITERATURE_PRIOR_UNCALIBRATED' ? 'Literature-informed, uncalibrated' : 'Provisional, uncalibrated'}</span>
        </p>}
      </div>
    </section>

    <main className="grid">
      <section className={`card camera ${decision === 'POSSIBLE_PERSON' ? 'glow' : ''}`}>
        <div className="card-head"><h2>Camera</h2>
          <span className={`chip ${state?.camera.available && live ? 'ok' : ''}`}><i className="dot" />{pretty(state?.camera.status || 'connecting')}</span></div>
        <div className="stage">
          {frames.map((frame, index) => <img key={frame.frameId} src={frame.url} alt={index === frames.length - 1 ? 'Live camera frame' : ''}
            className={index === frames.length - 1 ? 'frame enter' : 'frame'} />)}
          {!current && <div className="stage-empty"><div className="spinner" aria-hidden="true" />
            <p>{backendError ? 'Camera preview unavailable' : state?.camera.url ? 'Waiting for the camera…' : 'Connect the camera below'}</p>
            {state?.camera.error && <small>{state.camera.error}</small>}</div>}
          {boxes && <svg className="boxes" viewBox={`0 0 ${boxes.input_width} ${boxes.input_height}`} preserveAspectRatio="xMidYMid meet">
            {boxes.detections.map(({ box_xyxy: [x1, y1, x2, y2], score }, index) => <g key={index}>
              <rect rx="4" style={{ x: x1, y: y1, width: x2 - x1, height: y2 - y1 }} />
              <text style={{ transform: `translate(${x1 + 4}px, ${Math.max(y1 - 5, 10)}px)` }}>Person {Math.round(score * 100)}%</text></g>)}</svg>}
          {edgeOnFrame && frameSize && <svg className={`crop ${edgeOnFrame.person ? 'hit' : ''}`} aria-hidden="true"
            viewBox={`0 0 ${frameSize.width} ${frameSize.height}`} preserveAspectRatio="xMidYMid meet">
            <rect x={(frameSize.width - Math.min(frameSize.width, frameSize.height)) / 2}
              y={(frameSize.height - Math.min(frameSize.width, frameSize.height)) / 2}
              width={Math.min(frameSize.width, frameSize.height)} height={Math.min(frameSize.width, frameSize.height)} rx="6" /></svg>}
          {current && <span className="stage-tag">{testPattern ? 'Test pattern' : 'Live'} · {current.frameId.replace('camera-', '#')}</span>}
          {detection?.status === 'READY' && !!detection.person_count &&
            <span className="stage-badge">{detection.person_count === 1 ? '1 person' : `${detection.person_count} people`} in view</span>}
        </div>
        <div className="detectors">
          <div className={`detector ${edge?.status === 'READY' && edge.person ? 'hit' : ''}`}>
            <span className="where">On ESP32 · TFLite Micro</span>
            <strong>{edge?.status === 'READY' ? (edge.person ? 'Person' : 'No person') : sentence(edge?.status || 'connecting')}</strong>
            {edge?.status === 'READY' && <>
              <div className="bar"><div style={{ width: `${(edge.score ?? 0) * 100}%` }} /></div>
              <small>score {percent(edge.score)} · {edge.infer_ms} ms on device · 96×96 centre crop</small></>}
            {edge?.status === 'NOT_REPORTED' && <small>Node firmware does not send on-device results</small>}
          </div>
          <div className={`detector ${detection?.status === 'READY' && detection.person_count ? 'hit' : ''}`}>
            <span className="where">On laptop · YOLOX-Nano</span>
            <strong>{detection?.status === 'READY' ? (detection.person_count
              ? `${detection.person_count === 1 ? '1 person' : `${detection.person_count} people`}` : 'No person') : sentence(detection?.status || 'connecting')}</strong>
            {detection?.status === 'READY' && <>
              <div className="bar"><div style={{ width: `${Math.max(0, ...detection.detections.map(d => d.score)) * 100}%` }} /></div>
              <small>best {percent(Math.max(0, ...detection.detections.map(d => d.score)))} · {number(detection.inference_ms, 0)} ms on laptop · boxes</small></>}
          </div>
        </div>
        <div className="meta">
          <span>{number(state?.camera.receive_age_ms != null ? state.camera.receive_age_ms / 1000 : null)} s old</span>
          {state?.camera.frame?.node_rssi_dbm != null && <span>Wi-Fi {state.camera.frame.node_rssi_dbm} dBm</span>}
        </div>
      </section>

      <div className="side">
        <section className="card">
          <div className="card-head"><h2>Radar</h2>
            <span className={`chip ${radar ? 'ok' : ''}`}><i className="dot" />{radar ? 'Live' : pretty(state?.radar.status || 'not configured')}</span></div>
          <RadarView reading={radar} live={!!radar} />
          <p className="radar-caption">{radar ? radarSummary(radar) : state?.radar.error || 'Radar not streaming'}</p>
          <div className="legend"><span><i className="moving" />Moving</span><span><i className="still" />Still</span>
            <span className="muted">Distance only · direction not measured</span></div>
        </section>

        <section className="card">
          <div className="card-head"><h2>Thermal</h2><span className="chip warn">Simulated</span></div>
          <div className="thermal">
            <div className="temp">{number(ir?.object_temperature_c)}<small>°C</small></div>
            <svg viewBox="0 0 300 60" preserveAspectRatio="none" className="spark" aria-hidden="true">
              {spark.length > 1 && <><polygon points={`0,60 ${spark.join(' ')} ${spark[spark.length - 1].split(',')[0]},60`} />
                <polyline points={spark.join(' ')} /></>}</svg>
          </div>
          <select aria-label="Simulated thermal scenario" disabled={disabled} value={state?.ir.scenario || 'baseline'}
            onChange={event => void act('/api/config/ir', { scenario: event.target.value })}>
            {SCENARIOS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
          <p className="note">IR sensor unavailable · laptop-generated values · never used for detection</p>
        </section>
      </div>
    </main>

    <section className="card scene-card">
      <div className="card-head"><h2>Scene</h2>
        <div className="segmented compact" role="radiogroup" aria-label="Scene view">
          <span className="thumb" style={{ transform: `translateX(${view === 'overhead' ? 100 : 0}%)` }} />
          {([['perspective', 'Perspective'], ['overhead', 'Overhead']] as const).map(([value, label]) =>
            <button key={value} role="radio" aria-checked={view === value} className={view === value ? 'active' : ''}
              onClick={() => setView(value)}>{label}</button>)}
        </div></div>
      <div className="scene-wrap">
        <Scene3D person={scenePerson} view={view} />
        <span className="stage-tag">Illustrative</span>
        <span className={`scene-label ${scenePerson.state}`}>{scenePerson.state === 'present'
          ? `Person · ${seen?.rangeKnown ? `≈ ${scenePerson.distanceM.toFixed(1)} m` : 'distance unknown'}`
          : scenePerson.state === 'last_seen' ? `Last seen ${Math.round((Date.now() - (seen?.at ?? 0)) / 1000)} s ago` : 'No one placed'}</span>
      </div>
      <p className="note">Generic figure, not a body reconstruction. Distance comes from the radar and left/right from the
        camera box (assumed 50° lens); both are uncalibrated, so the position is schematic.</p>
    </section>

    <div className="drawers">
      <details className="card drawer">
        <summary>Assessment details</summary>
        <div className="drawer-body">
          <div className="kv"><span>Evidence index</span><b>{fusion?.index != null ? fusion.index.toFixed(2) : '—'}</b></div>
          <div className="kv"><span>Coverage</span><b>{percent(fusion?.coverage)}</b></div>
          <div className="kv"><span>Condition</span><b>{state?.profile.label || '—'}</b></div>
          {Object.entries(state?.profile.weights || {}).map(([name, weight]) =>
            <div className="kv" key={name}><span>{name === 'ir' ? 'IR weight (simulated)' : `${name} weight`}</span>
              <b>{percent(weight)}{state?.profile.prior_weights && state.profile.prior_weights[name] !== weight ? ` (prior ${percent(state.profile.prior_weights[name])})` : ''}</b></div>)}
          {state?.profile.ir_rule && <p className="note">{state.profile.ir_rule}</p>}
          <div className="kv"><span>Detector</span><b>{detection?.model ? `${detection.model.name.split(' (')[0]} · ${detection.model.licence}` : '—'}</b></div>
          <p className="note">{state?.assessment.reason} Camera/radar alignment is unverified and detector accuracy
            on this camera is not yet evaluated.</p>
        </div>
      </details>

      <details className="card drawer">
        <summary>Connections</summary>
        <div className="drawer-body">
          <form className="field" onSubmit={event => { event.preventDefault(); void act('/api/config/camera', { url: cameraUrl || null }); }}>
            <label htmlFor="camera-url">Camera capture URL</label>
            <div className="row"><input id="camera-url" type="url" value={cameraUrl} placeholder="http://ares.local/capture"
              onChange={event => setCameraUrl(event.target.value)} /><button disabled={disabled} type="submit">Apply</button></div>
          </form>
          <div className="field">
            <label htmlFor="radar-device">Radar Bluetooth address</label>
            <div className="row"><input id="radar-device" list="radar-options" value={radarAddress} placeholder="Scan or enter address"
              disabled={disabled || state?.radar.enabled} onChange={event => setRadarAddress(event.target.value)} />
              <button disabled={disabled || state?.radar.enabled} onClick={async () => {
                const result = await act('/api/radar/scan', { timeout: 8 });
                if (result) { setDevices(result.devices); if (result.devices.length === 1) setRadarAddress(result.devices[0].address); }
              }}>{busy ? 'Scanning…' : 'Scan'}</button>
              <button disabled={disabled || (!state?.radar.enabled && !radarAddress)} onClick={() => void act('/api/config/radar', {
                enabled: !state?.radar.enabled, address: state?.radar.enabled ? null : radarAddress })}>
                {state?.radar.enabled ? 'Disconnect' : 'Connect'}</button></div>
            <datalist id="radar-options">{devices.map(device => <option key={device.address} value={device.address}>{device.name} · {device.rssi_dbm} dBm</option>)}</datalist>
            <p className="note">Close the HLKRadarTool app first; the radar accepts one Bluetooth connection.</p>
          </div>
        </div>
      </details>
    </div>

    <footer>
      <span>{state?.recording.active ? `Recording ${state.recording.session_id?.slice(0, 8)} · ${state.recording.events} events · ${state.recording.frames} frames`
        : state?.recording.error || 'All inputs are labelled by source · processing runs on this laptop'}</span>
      {state?.recording.session_id && !state.recording.active &&
        <a href={`/api/recordings/${state.recording.session_id}/events`} download>Download last session</a>}
    </footer>
  </div>;
}
