import math
import wave
import io
import array
import time
import platform
import subprocess
import os
import tempfile
from collections import defaultdict

try:
    import numpy as _np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

SAMPLE_RATE = 44100

INSTRUMENTS = {
    '플루트', '클라리넷', '오보에', '바순', '색소폰',
    '트럼펫', '트롬본', '유포늄', '호른', '튜바',
}

# 샵이 있는 음이름이 먼저 매칭되도록 긴 이름 우선 정렬
NOTE_SEMITONES = {
    '도#': 1,  '도': 0,
    '레#': 3,  '레': 2,
    '미':  4,
    '파#': 6,  '파': 5,
    '솔#': 8,  '솔': 7,
    '라#': 10, '라': 9,
    '시':  11,
}
_NOTE_KEYS = sorted(NOTE_SEMITONES, key=len, reverse=True)

BEAT_VALUES = {
    '악!':    1.0,    '악!!':   2.0,  '악!!!':  3.0,  '악!!!!': 4.0,
    '아악!':  0.5,  '아악!!': 0.25, '아악!!!': 0.125, '아악!!!!': 0.0625,
}

INSTRUMENT_PROFILES = {
    '플루트':   {'harmonics': [(1,1.0),(2,0.18),(3,0.02)],
                 'attack':0.05,'decay':0.02,'sustain':0.87,'release':0.10,
                 'vibrato_rate':5.2,'vibrato_depth':0.007},
    '클라리넷': {'harmonics': [(1,1.0),(3,0.60),(5,0.30),(7,0.08),(9,0.02)],
                 'attack':0.02,'decay':0.01,'sustain':0.93,'release':0.04,
                 'vibrato_rate':0,'vibrato_depth':0},
    '오보에':   {'harmonics': [(1,1.0),(2,0.55),(3,0.35),(4,0.18),(5,0.08),(6,0.03)],
                 'attack':0.02,'decay':0.03,'sustain':0.80,'release':0.06,
                 'vibrato_rate':5.5,'vibrato_depth':0.007},
    '바순':     {'harmonics': [(1,1.0),(2,0.55),(3,0.28),(4,0.12),(5,0.05)],
                 'attack':0.07,'decay':0.04,'sustain':0.77,'release':0.11,
                 'vibrato_rate':4.0,'vibrato_depth':0.006},
    '색소폰':   {'harmonics': [(1,1.0),(2,0.65),(3,0.42),(4,0.22),(5,0.12),(6,0.06)],
                 'attack':0.04,'decay':0.03,'sustain':0.83,'release':0.08,
                 'vibrato_rate':4.5,'vibrato_depth':0.007},
    '트럼펫':   {'harmonics': [(1,1.0),(2,0.75),(3,0.52),(4,0.32),(5,0.18),(6,0.08),(7,0.04)],
                 'attack':0.01,'decay':0.02,'sustain':0.91,'release':0.03,
                 'vibrato_rate':0,'vibrato_depth':0},
    '트롬본':   {'harmonics': [(1,1.0),(2,0.62),(3,0.40),(4,0.25),(5,0.14),(6,0.06)],
                 'attack':0.04,'decay':0.02,'sustain':0.87,'release':0.07,
                 'vibrato_rate':4.0,'vibrato_depth':0.006},
    '유포늄':   {'harmonics': [(1,1.0),(2,0.52),(3,0.30),(4,0.16),(5,0.07)],
                 'attack':0.05,'decay':0.03,'sustain':0.85,'release':0.09,
                 'vibrato_rate':4.5,'vibrato_depth':0.006},
    '호른':     {'harmonics': [(1,1.0),(2,0.48),(3,0.28),(4,0.15),(5,0.06)],
                 'attack':0.08,'decay':0.03,'sustain':0.82,'release':0.11,
                 'vibrato_rate':5.0,'vibrato_depth':0.007},
    '튜바':     {'harmonics': [(1,1.0),(2,0.38),(3,0.18),(4,0.09),(5,0.03)],
                 'attack':0.08,'decay':0.04,'sustain':0.77,'release':0.13,
                 'vibrato_rate':0,'vibrato_depth':0},
}

_DEFAULT_PROFILE = {'harmonics':[(1,1.0)],
                    'attack':0.005,'decay':0.005,'sustain':1.0,'release':0.005,
                    'vibrato_rate':0,'vibrato_depth':0}


class MusicManager:
    def __init__(self, error_class, parse_number_func):
        self.MarineError = error_class
        self._parse_marine_int = parse_number_func
        self.scores = []            # 전역 악보 저장소 (군악대 퇴장 후에도 유지)
        self.band = None            # 현재 군악대 인원수 (없으면 None)
        self.instruments = []       # 군악병별 악기
        self.assigned_scores = []   # 군악병별 악보
        self.pending_delay = None   # 대기하겠습니다로 설정된 초
        self._browser_time = 0.0   # 브라우저 WebAudio 스케줄링용 누적 시간(초)

    # ── 군악대 도열 ────────────────────────────────────────────

    def form_band(self, count, line_num):
        """군악대 도열 (정수)"""
        if self.band is not None:
            raise self.MarineError(
                f"[줄 {line_num}] 런타임 오류: 이미 군악대가 있다! 먼저 총원 헤쳐!"
            )
        if count < 1:
            raise self.MarineError(
                f"[줄 {line_num}] 런타임 오류: 군악대 인원수가 1보다 작다!"
            )
        self.band = count
        self.instruments = [None] * count
        self.assigned_scores = [None] * count
        self.pending_delay = None

    def _assert_no_pending_delay(self, line_num):
        if self.pending_delay is not None:
            raise self.MarineError(
                f"[줄 {line_num}] 런타임 오류: '대기하겠습니다' 다음에는 반드시 '연주 시작'이 와야 한다!"
            )

    # ── 악기 설정 ──────────────────────────────────────────────

    def set_instruments(self, instrument_list, line_num):
        """군악대! (악기)... 준비"""
        self._assert_no_pending_delay(line_num)
        if self.band is None:
            raise self.MarineError(
                f"[줄 {line_num}] 런타임 오류: 군악대를 불러오지 않고 악기를 설정했다!"
            )
        if len(instrument_list) != self.band:
            raise self.MarineError(
                f"[줄 {line_num}] 런타임 오류: 악기 개수({len(instrument_list)})와 "
                f"군악대 인원수({self.band})가 일치하지 않는다!"
            )
        for inst in instrument_list:
            if inst not in INSTRUMENTS:
                raise self.MarineError(
                    f"[줄 {line_num}] 런타임 오류: '{inst}'은 군악대 악기가 아니다!"
                )
        self.instruments = list(instrument_list)

    # ── 악보 저장 ──────────────────────────────────────────────

    def save_score(self, block_tokens, line_num):
        """소중히 간직할 수 있도록 필승 (악보) 받아쓰"""
        self._assert_no_pending_delay(line_num)
        score = self._parse_score(block_tokens, line_num)
        self.scores.append(score)

    # ── 악보 숙지 ──────────────────────────────────────────────

    def learn_score(self, musician_idx, score_idx, line_num):
        """(군악병N) 제대로 숙지할 수 있도록 필승 숙지완료하였습니다M 받아쓰"""
        self._assert_no_pending_delay(line_num)
        if self.band is None:
            raise self.MarineError(
                f"[줄 {line_num}] 런타임 오류: 군악대를 불러오지 않고 악보를 숙지했다!"
            )
        if musician_idx < 1 or musician_idx > self.band:
            raise self.MarineError(
                f"[줄 {line_num}] 런타임 오류: {musician_idx}번 군악병이 없다! "
                f"현재 군악대는 {self.band}명이다!"
            )
        if score_idx < 1 or score_idx > len(self.scores):
            raise self.MarineError(
                f"[줄 {line_num}] 런타임 오류: {score_idx}번 악보가 저장되어 있지 않다!"
            )
        self.assigned_scores[musician_idx - 1] = self.scores[score_idx - 1]

    # ── 대기 설정 ──────────────────────────────────────────────

    def set_delay(self, seconds, line_num):
        """군악대! 대기하겠습니다 (정수)"""
        self._assert_no_pending_delay(line_num)
        if self.band is None:
            raise self.MarineError(
                f"[줄 {line_num}] 런타임 오류: 군악대를 불러오지 않고 대기했다!"
            )
        if seconds < 1:
            raise self.MarineError(
                f"[줄 {line_num}] 런타임 오류: 대기 시간은 1초 이상이어야 한다!"
            )
        self.pending_delay = seconds

    # ── 연주 ───────────────────────────────────────────────────

    def play(self, line_num):
        """군악대! 연주 시작"""
        if self.band is None:
            raise self.MarineError(
                f"[줄 {line_num}] 런타임 오류: 군악대를 불러오지 않고 연주했다!"
            )
        for i, score in enumerate(self.assigned_scores):
            if score is None:
                raise self.MarineError(
                    f"[줄 {line_num}] 런타임 오류: {i + 1}번 군악병이 악보를 숙지하지 않았다!"
                )
        if self.pending_delay is not None:
            delay = self.pending_delay
            self.pending_delay = None
            try:
                import js  # Pyodide 감지: 브라우저에서는 시간 오프셋만 앞당김
                self._browser_time += delay
            except ModuleNotFoundError:
                time.sleep(delay)
        self._mix_and_play(self.assigned_scores, self.instruments)

    # ── 퇴장 ───────────────────────────────────────────────────

    def dismiss(self, line_num):
        """군악대! 총원 헤쳐"""
        self._assert_no_pending_delay(line_num)
        if self.band is None:
            raise self.MarineError(
                f"[줄 {line_num}] 런타임 오류: 군악대를 불러오지 않고 퇴장시켰다!"
            )
        self.band = None
        self.instruments = []
        self.assigned_scores = []
        self.pending_delay = None

    # ── 악보 파싱 ──────────────────────────────────────────────

    def _parse_score(self, block_tokens, line_num):
        lines = defaultdict(list)
        for tok, ln in block_tokens:
            lines[ln].append(tok)
        sorted_lines = [lines[ln] for ln in sorted(lines)]

        if not sorted_lines:
            raise self.MarineError(f"[줄 {line_num}] 악보 오류: 악보가 비어있다!")

        # 첫 줄: BPM (해병 정수)
        if len(sorted_lines[0]) != 1:
            raise self.MarineError(
                f"[줄 {line_num}] 악보 오류: 악보 첫 줄은 BPM 토큰 하나여야 한다!"
            )
        bpm = self._parse_marine_int(sorted_lines[0][0], line_num)
        if bpm <= 0:
            raise self.MarineError(f"[줄 {line_num}] 악보 오류: BPM은 1 이상이어야 한다!")

        # 나머지: 음줄 / 박자줄 쌍
        remaining = sorted_lines[1:]
        if len(remaining) % 2 != 0:
            raise self.MarineError(
                f"[줄 {line_num}] 악보 오류: 음줄과 박자줄의 쌍이 맞지 않는다!"
            )

        notes = []
        for i in range(0, len(remaining), 2):
            note_line = remaining[i]
            beat_line = remaining[i + 1]
            if len(note_line) != len(beat_line):
                raise self.MarineError(
                    f"[줄 {line_num}] 악보 오류: 음과 박자의 개수가 일치하지 않는다!"
                )
            for note_tok, beat_tok in zip(note_line, beat_line):
                note = self._parse_note(note_tok, line_num)
                beat = self._parse_beat(beat_tok, line_num)
                notes.append((note, beat))

        return {'bpm': bpm, 'notes': notes}

    def _parse_note(self, token, line_num):
        if token == '악':
            return {'is_rest': True, 'semitone': 0, 'octave': 0}
        for name in _NOTE_KEYS:
            if token.startswith(name):
                rest = token[len(name):]
                if all(c == '!' for c in rest):
                    return {
                        'is_rest': False,
                        'semitone': NOTE_SEMITONES[name],
                        'octave': len(rest),
                    }
        raise self.MarineError(
            f"[줄 {line_num}] 악보 오류: '{token}'은 올바른 음 표기가 아니다!"
        )

    def _parse_beat(self, token, line_num):
        if token not in BEAT_VALUES:
            raise self.MarineError(
                f"[줄 {line_num}] 악보 오류: '{token}'은 올바른 박자 표기가 아니다!"
            )
        return BEAT_VALUES[token]

    # ── 오디오 생성 및 재생 ────────────────────────────────────

    def _note_to_freq(self, semitone, octave):
        # 0옥타브 = MIDI 4옥타브 (C4 = 261.63Hz, A4 = 440Hz)
        midi_note = 12 * (octave + 4) + semitone
        return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))

    def _generate_samples(self, score, instrument=None):
        profile = INSTRUMENT_PROFILES.get(instrument, _DEFAULT_PROFILE)
        beat_sec = 60.0 / score['bpm']
        out = []
        for note, beat in score['notes']:
            n = max(1, int(SAMPLE_RATE * beat * beat_sec))
            if note['is_rest']:
                out.extend([0.0] * n)
            else:
                freq = self._note_to_freq(note['semitone'], note['octave'])
                if _HAS_NUMPY:
                    out.extend(self._synthesize_note_np(freq, n, profile))
                else:
                    out.extend(self._synthesize_note_py(freq, n, profile))
        return out

    def _synthesize_note_np(self, freq, n, profile):
        t = _np.arange(n) / SAMPLE_RATE
        attack_n  = min(int(SAMPLE_RATE * profile['attack']),  n // 4)
        decay_n   = min(int(SAMPLE_RATE * profile['decay']),   n // 4)
        release_n = min(int(SAMPLE_RATE * profile['release']), n // 4)
        sustain   = profile['sustain']
        env = _np.full(n, float(sustain))
        if attack_n  > 0: env[:attack_n]                     = _np.linspace(0.0, 1.0,     attack_n)
        if decay_n   > 0: env[attack_n:attack_n + decay_n]   = _np.linspace(1.0, sustain, decay_n)
        if release_n > 0: env[max(0, n - release_n):]        = _np.linspace(sustain, 0.0, n - max(0, n - release_n))
        use_vibrato = profile['vibrato_rate'] > 0
        if use_vibrato:
            vib_depth = profile['vibrato_depth'] * min(1.0, 440.0 / max(freq, 1.0))
            vib_onset = _np.clip(_np.arange(n) / max(n * 0.30, 1.0), 0.0, 1.0)
            vib = 1.0 + vib_depth * vib_onset * _np.sin(2.0 * _np.pi * profile['vibrato_rate'] * t)
        nyquist = SAMPLE_RATE / 2.0
        harmonics = [(h, a) for h, a in profile['harmonics'] if freq * h < nyquist] or [(1, 1.0)]
        total_amp = sum(a for _, a in harmonics)
        signal = _np.zeros(n)
        for harmonic, amplitude in harmonics:
            if use_vibrato:
                # sin(f·v·t)는 v가 시변일 때 변조 지수가 t에 비례해 발산 → cumsum으로 올바른 위상 적분
                phase = _np.cumsum(2.0 * _np.pi * freq * harmonic * vib / SAMPLE_RATE)
                signal += amplitude * _np.sin(phase)
            else:
                signal += amplitude * _np.sin(2.0 * _np.pi * freq * harmonic * t)
        signal = signal / total_amp * env
        return signal.tolist()

    def _synthesize_note_py(self, freq, n, profile):
        attack_n  = min(int(SAMPLE_RATE * profile['attack']),  n // 4)
        decay_n   = min(int(SAMPLE_RATE * profile['decay']),   n // 4)
        release_n = min(int(SAMPLE_RATE * profile['release']), n // 4)
        sustain   = profile['sustain']
        nyquist   = SAMPLE_RATE / 2.0
        harmonics = [(h, a) for h, a in profile['harmonics'] if freq * h < nyquist] or [(1, 1.0)]
        total_amp = sum(a for _, a in harmonics)
        phases    = [0.0] * len(harmonics)
        vib_depth = (profile['vibrato_depth'] * min(1.0, 440.0 / max(freq, 1.0))
                     if profile['vibrato_rate'] else 0.0)
        vib_onset_dur = max(n * 0.30, 1.0)
        out = []
        for i in range(n):
            if   i < attack_n:                      env = i / attack_n if attack_n else 1.0
            elif i < attack_n + decay_n:            env = 1.0 - (1.0 - sustain) * (i - attack_n) / decay_n if decay_n else sustain
            elif i >= n - release_n and release_n:  env = sustain * (n - i) / release_n
            else:                                   env = sustain
            t = i / SAMPLE_RATE
            vib_onset = min(1.0, i / vib_onset_dur)
            vib = (1.0 + vib_depth * vib_onset * math.sin(2.0 * math.pi * profile['vibrato_rate'] * t)
                   if profile['vibrato_rate'] else 1.0)
            v = 0.0
            for k, (harmonic, amplitude) in enumerate(harmonics):
                phases[k] += 2.0 * math.pi * freq * harmonic * vib / SAMPLE_RATE
                v += amplitude * math.sin(phases[k])
            out.append(v / total_amp * env)
        return out

    def _schedule_browser(self, scores, instruments):
        """브라우저 전용: WAV 생성 없이 음표 파라미터를 JS에 전달해 WebAudio로 합성"""
        import js
        import json as _json

        max_duration = 0.0
        for score, instrument in zip(scores, instruments):
            profile  = INSTRUMENT_PROFILES.get(instrument, _DEFAULT_PROFILE)
            beat_sec = 60.0 / score['bpm']
            # harmonics는 JSON 문자열로 전달 — Pyodide 프록시 변환 문제 없이 안전
            harmonics_json = _json.dumps([[h, a] for h, a in profile['harmonics']])
            t = 0.0
            for note, beat in score['notes']:
                duration = beat * beat_sec
                if not note['is_rest']:
                    freq = self._note_to_freq(note['semitone'], note['octave'])
                    js.marineScheduleNote(
                        self._browser_time + t,
                        duration,
                        freq,
                        harmonics_json,
                        profile['attack'],
                        profile['decay'],
                        profile['sustain'],
                        profile['release'],
                        profile['vibrato_rate'],
                        profile['vibrato_depth'],
                    )
                t += duration
            max_duration = max(max_duration, t)

        self._browser_time += max_duration

    def _mix_and_play(self, scores, instruments):
        try:
            import js  # Pyodide 감지: 브라우저에서는 WebAudio 스케줄링으로 처리
            self._schedule_browser(scores, instruments)
            return
        except ModuleNotFoundError:
            pass

        all_samples = [self._generate_samples(s, inst)
                       for s, inst in zip(scores, instruments)]
        max_len = max(len(s) for s in all_samples)

        # 짧은 악보는 침묵으로 패딩
        for s in all_samples:
            if len(s) < max_len:
                s.extend([0.0] * (max_len - len(s)))

        # 믹싱 (평균)
        k = len(all_samples)
        mixed = [sum(all_samples[i][j] for i in range(k)) / k for j in range(max_len)]

        # 정규화
        peak = max((abs(v) for v in mixed), default=1.0)
        if peak > 0:
            scale = 0.9 / peak
            mixed = [v * scale for v in mixed]

        # 16-bit PCM → WAV
        int_samples = array.array('h', (int(v * 32767) for v in mixed))
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(int_samples.tobytes())

        self._play_wav(buf.getvalue())


    def _play_wav(self, wav_bytes):
        # Windows 네이티브
        if platform.system() == 'Windows':
            import winsound
            winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
            return

        # 3순위: macOS / Linux
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(wav_bytes)
            tmp = f.name
        try:
            cmd = ['afplay', tmp] if platform.system() == 'Darwin' else ['aplay', tmp]
            subprocess.run(cmd, check=True)
        finally:
            os.unlink(tmp)
