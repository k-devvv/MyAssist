"""Offline transcription worker. Audio bytes are decoded and discarded in memory."""
import base64, io, json, logging, sys
from pathlib import Path
logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio
def emit(value): sys.stdout.write(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n'); sys.stdout.flush()
def main():
    model_dir=Path(sys.argv[1]) if len(sys.argv)>1 else Path('resources/models/base')
    model=WhisperModel(str(model_dir),device='cpu',compute_type='int8',cpu_threads=4)
    emit({'type':'ready'})
    for line in sys.stdin:
        raw=bytearray(); samples=None
        try:
            request=json.loads(line)
            if request.get('kind')=='shutdown': break
            raw.extend(base64.b64decode(request.get('audio',''),validate=True))
            if len(raw)>12*1024*1024: raise ValueError('Recording exceeds the 12 MB limit.')
            samples=decode_audio(io.BytesIO(raw),sampling_rate=16000)
            segments,_=model.transcribe(samples,beam_size=1,condition_on_previous_text=False,vad_filter=True)
            transcript=''.join(segment.text for segment in segments).strip()
            emit({'type':'transcript','id':request.get('id'),'text':transcript})
        except Exception as error: emit({'type':'error','id':request.get('id'),'message':str(error)[:240]})
        finally:
            if samples is not None:
                try: samples.fill(0)
                except Exception: pass
            raw[:]=b'\0'*len(raw)
    return 0
if __name__=='__main__': raise SystemExit(main())
