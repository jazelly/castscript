# castscript format, v0.1

A castscript is a UTF-8 plain-text file (`*.cast.txt`) that says **who reads each line, in which voice, with what emotion, and how long to pause**. It does not depend on any TTS engine. Each engine adapter translates what it can and reports what it cannot.

## Example

```
# Chapter 1: Rainy Night
@voice 旁白 = ref: voices/01_storyteller_raspy.wav
@voice 林风 = ref: voices/22_wuxia_hero.wav
@voice 掌柜 = design: 一位五十多岁的客栈掌柜，男声，热情圆滑，语速稍快。

旁白：那天夜里，雨下得很大。他推开客栈的门，抖了抖身上的水。
林风（低声，疲惫）：掌柜的，还有空房吗？
旁白：掌柜抬起头，愣了一下。
<pause 1>
掌柜（惊讶转为热情）：有，有，客官里边请！[笑]

---
旁白：第二天清晨……
```

## Rules

### Comments
A line starting with `#` is ignored.

### Voices
`@voice NAME = KIND: VALUE` defines a voice before it is used. Each `NAME` must be unique. A line starting with `@voice` that does not match this form is an error.

| KIND | VALUE | Meaning |
|---|---|---|
| `ref` | path to a WAV file, relative to the script | Clone this voice. A transcript file with the same name and a `.txt` extension must sit next to the WAV. |
| `design` | natural-language description | Create a voice from the description. |
| `preset` | engine speaker name | Use one of the engine's built-in speakers. |

### Lines
`NAME：TEXT` or `NAME（EMOTION）：TEXT`. Full-width and half-width colons and parentheses are both accepted. `NAME` must be a defined voice. `EMOTION` is free-form natural language (for example `愤怒地，语速加快`).

### Vocal events
`[笑]`, `[叹气]`, `[咳嗽]`, and `[清嗓子]` (laugh, sigh, cough, clear throat) may appear inside `TEXT`. Each engine translates them to its own tags and drops the ones it cannot render; a line that becomes empty is skipped and keeps only its pause. Subtitles never include them.

### Pauses
| Source | Silence after the previous line |
|---|---|
| next line follows directly | 0.4 s |
| one or more blank lines | 0.8 s |
| `---` (scene break) | 2.0 s |
| `<pause N>` or `<停顿 N>` | exactly N seconds (overrides the above); an error before the first line |

### Long lines
A renderer may split a long `TEXT` at sentence-ending punctuation (`。！？…`). Splits within one line add no pause.

### Any other line
Any other non-empty line is an error, and the error names the line number.

## Engine support

| Engine | `ref` | `design` | `preset` | Emotion | Vocal events |
|---|---|---|---|---|---|
| Breeze TTS 2 | yes | yes | no | yes, including with `ref` | all four |
| Qwen3-TTS | yes (Base model) | yes (VoiceDesign model) | yes (CustomVoice model) | with `design`/`preset`; not with `ref` | none |
| Chatterbox Multilingual V3 | yes | no | no | no | none |
| OmniVoice | yes | attribute list only, e.g. `男，老年，低音调` | no | no | `[笑]` `[叹气]` |
| KittenTTS 2 | yes | no | yes, e.g. `Chinese`, `Bruno` | only `angry` `contemplative` `excited` `joyful` `mundane` `nervous` `sad` `stern` `surprised` `tender` | `[笑]` `[叹气]` |
| Kokoro-82M | no | no | yes, e.g. `zf_xiaoxiao`, `af_heart` | no | none |
| Pocket TTS | yes (gated model) | no | yes, e.g. `alba` | no | none |
| VoxCPM2 | yes | yes | no | yes, including with `ref` | none |
| IndexTTS-2.5 | yes | no | no | yes | none |
| Audio8-TTS 0.6B | yes | no | no | no | none |
| dots.tts | yes | no | no | no | none |

Pauses are inserted by the renderer for every engine. Using a voice kind an engine lacks is an error. When an engine cannot honor an emotion, it warns and renders the line without the emotion.
