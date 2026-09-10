import React, { useState, useEffect, useRef } from 'react';
import { API_BASE_URL, apiFetch, apiUrl } from '../api';

export default function AIChatPanel({ defaultCollapsed = false }) {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [messages, setMessages] = useState([
    { 
      sender: 'agent', 
      text: '👋 **PPLE Voice & AI Assistant Online.** Siap membantu diagnosa MCSA, Vibrasi, DGA, Tribology, spesifikasi equipment, dan SOP pembangkit. Anda dapat **berbicara langsung (🎙️ Live Voice)**, mengetik, atau **mengunggah file dokumen/gambar (📎)**.', 
      type: 'info' 
    }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [attachedFile, setAttachedFile] = useState(null);
  const [isTyping, setIsTyping] = useState(false);
  
  // Voice Recognition (STT) & Speech Synthesis (TTS) State
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceOutputEnabled, setVoiceOutputEnabled] = useState(true);
  const [speechSupported, setSpeechSupported] = useState(false);

  // Enterprise Model & Provider Configuration
  const [provider, setProvider] = useState('gemini_enterprise');
  const [model, setModel] = useState('gemini-2.5-pro');
  const [showConfig, setShowConfig] = useState(false);

  const recognitionRef = useRef(null);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Initialize Web Speech API for Indonesian & English
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      setSpeechSupported(true);
      const recog = new SpeechRecognition();
      recog.continuous = false;
      recog.interimResults = true;
      recog.lang = 'id-ID';

      recog.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        setChatInput(transcript);
      };

      recog.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        setIsListening(false);
      };

      recog.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recog;
    }
  }, []);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Voice Output (TTS) Helper
  const speakText = (text) => {
    if (!voiceOutputEnabled || !('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel(); // Stop ongoing speech

    // Strip markdown formatting for cleaner speech
    const cleanText = text
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/\*(.*?)\*/g, '$1')
      .replace(/`(.*?)`/g, '$1')
      .replace(/•/g, '')
      .replace(/---/g, '')
      .replace(/\[.*?\]\(.*?\)/g, '')
      .slice(0, 450); // Limit length for snappy speech response

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = 'id-ID';
    utterance.rate = 1.05;
    utterance.pitch = 1.0;

    // Pick Indonesian voice if available
    const voices = window.speechSynthesis.getVoices();
    const idVoice = voices.find(v => v.lang.includes('id') || v.lang.includes('ID') || v.name.includes('Indonesian'));
    if (idVoice) utterance.voice = idVoice;

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  };

  const stopSpeaking = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  };

  // Toggle Microphone Input
  const toggleListening = () => {
    if (!speechSupported || !recognitionRef.current) {
      alert('Browser Anda tidak mendukung Web Speech API atau izin mikrofon belum diberikan.');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      stopSpeaking();
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err) {
        console.error('Failed to start speech recognition:', err);
      }
    }
  };

  const quickPrompts = [
    '⚡ Diagnosa Motor BFP 1A',
    '🌀 Cek Getaran IDF 1A',
    '⚠️ List Motor Alarm & High',
    '🛢️ Evaluasi Kualitas Oli',
    '🧪 Analisis DGA Trafo',
    '🛡️ Standar ISO 10816 & IEEE 519'
  ];

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setAttachedFile(e.target.files[0]);
    }
  };

  const removeAttachedFile = () => {
    setAttachedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const sendMessage = async (textToSend = null) => {
    const text = textToSend !== null ? textToSend : chatInput;
    if (!text.trim() && !attachedFile) return;

    // Stop listening or speaking
    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
    stopSpeaking();

    const fileInfo = attachedFile ? { name: attachedFile.name, size: (attachedFile.size / 1024).toFixed(1) + ' KB' } : null;
    const userMsg = { 
      sender: 'user', 
      text: text.trim() || `[Lampiran File: ${attachedFile?.name}]`, 
      file: fileInfo,
      type: 'normal' 
    };

    setMessages(prev => [...prev, userMsg]);
    setChatInput("");
    setIsTyping(true);

    const fileToSend = attachedFile;
    removeAttachedFile();

    try {
      let res;
      if (fileToSend) {
        const formData = new FormData();
        formData.append("message", text || `Analisis dokumen ${fileToSend.name}`);
        formData.append("file", fileToSend);
        formData.append("provider", provider);
        formData.append("model", model);

        res = await apiFetch(apiUrl('/api/agent/chat'), {
          method: 'POST',
          body: formData
        });
      } else {
        res = await apiFetch(apiUrl('/api/agent/chat'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            message: text,
            provider: provider,
            model: model
          })
        });
      }

      const data = await res.json();
      const replyText = data.reply || 'Tidak ada balasan dari server.';
      
      setMessages(prev => [...prev, { 
        sender: 'agent', 
        text: replyText, 
        aiEnhanced: data.ai_enhanced,
        activeSubagents: data.active_subagents || [],
        subagentTraces: data.subagent_traces || [],
        type: 'normal' 
      }]);

      // Automatically speak the response if voice is enabled
      speakText(replyText);

    } catch (_err) {
      console.error(`Backend API unavailable: ${API_BASE_URL}`, _err);
      setMessages(prev => [...prev, { 
        sender: 'agent', 
        text: `Gagal terhubung ke backend MCSA API (${API_BASE_URL}). Pastikan run_api.bat sudah dijalankan atau VITE_API_BASE_URL sudah benar.`,
        type: 'error' 
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage();
  };

  // Render Mini / Collapsed Trigger Button
  if (isCollapsed) {
    return (
      <div className="flex justify-end">
        <button
          onClick={() => setIsCollapsed(false)}
          className="flex items-center gap-2.5 px-4 py-2.5 rounded-2xl bg-panel2 border border-cyan/40 text-textMain shadow-neon hover:border-cyan hover:scale-[1.02] transition-all group"
          title="Buka AI Live Voice Assistant"
        >
          <div className="w-7 h-7 rounded-xl bg-cyan/20 border border-cyan/50 flex items-center justify-center text-xs text-cyan font-bold">
            🎙️
          </div>
          <div className="text-left">
            <span className="text-xs font-bold text-textMain group-hover:text-cyan transition-colors block">
              PPLE Voice & AI Assistant
            </span>
            <span className="text-[10px] text-muted flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-green animate-pulse"></span>
              Live Voice Ready
            </span>
          </div>
        </button>
      </div>
    );
  }

  // Render Full Chat Panel
  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5 flex flex-col h-full min-h-[500px] relative transition-all">
      {/* Header with Live Voice & Controls */}
      <div className="flex items-center justify-between pb-3 border-b border-line">
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-xl border flex items-center justify-center font-black text-xs transition-all ${isSpeaking ? 'border-purple bg-purple/20 text-purple animate-pulse shadow-[0_0_15px_rgba(168,85,247,0.4)]' : 'border-cyan/40 bg-cyan/10 text-cyan shadow-[0_0_12px_rgba(50,213,255,0.1)]'}`}>
            {isSpeaking ? '🔊' : 'AI'}
          </div>
          <div>
            <strong className="text-xs text-textMain block flex items-center gap-1.5">
              PPLE Voice & AI Agent
              {isSpeaking && <span className="text-[10px] text-purple font-normal animate-pulse">Speaking...</span>}
            </strong>
            <small className="block text-muted text-[10px]">CBM Diagnostics · Specs · Live Voice</small>
          </div>
        </div>
        
        <div className="flex items-center gap-1.5">
          {/* Gemini Enterprise Engine Selector Toggle */}
          <button
            onClick={() => setShowConfig(!showConfig)}
            className={`text-[10px] px-2 py-1 rounded border transition-colors flex items-center gap-1 ${
              provider === 'gemini_enterprise'
                ? 'border-purple bg-purple/15 text-purple font-bold shadow-[0_0_10px_rgba(168,85,247,0.2)]'
                : 'border-line text-muted hover:text-textMain'
            }`}
            title="Konfigurasi AI Engine & Provider"
          >
            <span>🛡️</span>
            <span className="hidden sm:inline">Enterprise</span>
          </button>

          {/* TTS Voice Speaker Toggle */}
          <button
            onClick={() => {
              if (isSpeaking) stopSpeaking();
              setVoiceOutputEnabled(!voiceOutputEnabled);
            }}
            className={`text-[10px] px-2 py-1 rounded border transition-colors flex items-center gap-1 ${voiceOutputEnabled ? 'border-cyan bg-cyan/10 text-cyan' : 'border-line text-muted hover:text-textMain'}`}
            title={voiceOutputEnabled ? 'Matikan Suara AI' : 'Aktifkan Suara AI (TTS)'}
          >
            <span>{voiceOutputEnabled ? '🔊 Voice' : '🔇 Mute'}</span>
          </button>

          <button 
            onClick={() => {
              stopSpeaking();
              setMessages([{ sender: 'agent', text: 'Riwayat percakapan telah dibersihkan. Silakan ajukan pertanyaan atau gunakan suara (🎙️).', type: 'info' }]);
            }}
            className="text-[10px] text-muted hover:text-textMain px-2 py-1 rounded border border-line"
            title="Reset Chat"
          >
            Clear
          </button>

          <button 
            onClick={() => {
              stopSpeaking();
              setIsCollapsed(true);
            }}
            className="text-xs text-muted hover:text-cyan px-2 py-1 rounded border border-line hover:border-cyan transition-colors flex items-center gap-1 font-bold"
            title="Sembunyikan Chat Panel"
          >
            <span>−</span> Hide
          </button>
        </div>
      </div>

      {/* Enterprise Configuration Drawer */}
      {showConfig && (
        <div className="my-2 p-3 rounded-xl bg-panel2 border border-purple/40 text-xs flex flex-col gap-2.5 animate-fade-in shadow-neon">
          <div className="flex justify-between items-center pb-1.5 border-b border-line">
            <span className="text-[10px] font-bold text-purple uppercase tracking-wider flex items-center gap-1">
              <span>🛡️</span> Gemini Enterprise &amp; Vertex AI Settings
            </span>
            <span className="text-[9px] text-green font-mono">Zero Data Retention</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[9px] text-muted block mb-1">AI Provider</label>
              <select
                value={provider}
                onChange={(e) => {
                  setProvider(e.target.value);
                  if (e.target.value === 'gemini_enterprise') setModel('gemini-2.5-pro');
                  else if (e.target.value === 'gemini') setModel('gemini-2.5-flash');
                  else if (e.target.value === 'groq') setModel('llama-3.3-70b-versatile');
                }}
                className="w-full bg-panel border border-line rounded p-1.5 text-[11px] text-textMain outline-none focus:border-cyan"
              >
                <option value="gemini_enterprise">🛡️ Gemini Enterprise (Vertex AI)</option>
                <option value="gemini">⚡ Google AI Studio</option>
                <option value="groq">🚀 Groq (Llama 3.3 70B)</option>
                <option value="ollama">💻 Ollama (Local Offline)</option>
              </select>
            </div>
            <div>
              <label className="text-[9px] text-muted block mb-1">Model Architecture</label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full bg-panel border border-line rounded p-1.5 text-[11px] text-textMain outline-none focus:border-cyan"
              >
                {provider === 'gemini_enterprise' ? (
                  <>
                    <option value="gemini-2.5-pro">gemini-2.5-pro (High Reasoning)</option>
                    <option value="gemini-2.5-flash">gemini-2.5-flash (Real-Time)</option>
                    <option value="gemini-1.5-pro">gemini-1.5-pro (2M Context)</option>
                  </>
                ) : provider === 'gemini' ? (
                  <>
                    <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                    <option value="gemini-2.0-flash">gemini-2.0-flash</option>
                    <option value="gemini-1.5-flash">gemini-1.5-flash</option>
                  </>
                ) : (
                  <option value={model}>{model}</option>
                )}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Live Voice Audio Wave Visualizer Banner (When Mic is Listening) */}
      {isListening && (
        <div className="my-2 p-2.5 rounded-xl bg-cyan/10 border border-cyan flex items-center justify-between animate-fade-in shadow-neon">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red animate-ping"></span>
            <span className="text-xs font-bold text-cyan">Mendengarkan Suara Anda...</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-1 h-3 bg-cyan animate-pulse"></span>
            <span className="w-1 h-5 bg-cyan animate-pulse delay-75"></span>
            <span className="w-1 h-2 bg-cyan animate-pulse delay-150"></span>
            <span className="w-1 h-6 bg-cyan animate-pulse delay-100"></span>
            <span className="w-1 h-4 bg-cyan animate-pulse delay-200"></span>
          </div>
          <button
            type="button"
            onClick={toggleListening}
            className="px-2 py-0.5 rounded bg-red/20 text-red border border-red/40 text-[10px] font-bold hover:bg-red/30 transition-colors"
          >
            Selesai
          </button>
        </div>
      )}

      {/* Message Stream */}
      <div className="flex flex-col gap-2.5 my-3 overflow-y-auto pr-1 flex-1 max-h-[320px]">
        {messages.map((msg, idx) => (
          <div 
            key={idx} 
            className={`rounded-xl p-3 text-xs leading-relaxed border transition-all ${
              msg.sender === 'user' 
                ? 'border-line bg-panel2 text-textMain ml-4' 
                : (msg.type === 'error' ? 'border-red/40 bg-red/5 text-red mr-3' : 'border-cyan/30 bg-cyan/5 text-textMain mr-3')
            }`}
          >
            <div className="flex justify-between text-muted text-[9px] uppercase tracking-wider mb-1 font-semibold">
              <span className={msg.sender === 'user' ? 'text-muted' : 'text-cyan'}>
                {msg.sender === 'user' ? 'Engineer' : 'PPLE Agent'}
              </span>
              <div className="flex items-center gap-1.5">
                {msg.aiEnhanced && (
                  <span className="text-[9px] text-purple font-mono font-bold">✨ Gemini AI</span>
                )}
                {msg.sender === 'agent' && (
                  <button 
                    onClick={() => speakText(msg.text)}
                    className="text-[10px] text-muted hover:text-cyan transition-colors"
                    title="Dengarkan Suara"
                  >
                    🔊
                  </button>
                )}
              </div>
            </div>

            {/* Active Specialist Sub-Agents Badges */}
            {msg.activeSubagents && msg.activeSubagents.length > 0 && (
              <div className="mb-2 flex flex-wrap gap-1">
                {msg.activeSubagents.map((sa, saIdx) => (
                  <span key={saIdx} className="px-1.5 py-0.5 rounded bg-panel border border-cyan/30 text-[9px] text-cyan font-bold flex items-center gap-1">
                    <span>{sa.icon}</span>
                    <span>{sa.name.replace('Specialist Agent', '').replace('Specialist', '')}</span>
                  </span>
                ))}
              </div>
            )}

            {/* Attached file chip in message */}
            {msg.file && (
              <div className="mb-2 p-1.5 rounded bg-panel border border-line inline-flex items-center gap-1.5 text-[10px] text-cyan">
                <span>📄</span>
                <span className="font-semibold">{msg.file.name}</span>
                <span className="text-muted">({msg.file.size})</span>
              </div>
            )}

            <div 
              className="whitespace-pre-line break-words space-y-1"
              dangerouslySetInnerHTML={{ 
                __html: msg.text
                  .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                  .replace(/\*(.*?)\*/g, '<em>$1</em>')
                  .replace(/\n/g, '<br/>')
              }} 
            />

            {/* Expandable Multi-Agent Reasoning Trace */}
            {msg.subagentTraces && msg.subagentTraces.length > 0 && (
              <details className="mt-2.5 p-2 rounded-xl bg-panel border border-line text-[11px] group">
                <summary className="cursor-pointer font-bold text-cyan flex items-center justify-between select-none">
                  <span className="flex items-center gap-1.5">
                    <span>🤖</span> Jejak Kolaborasi Sub-Agent ({msg.subagentTraces.length} Agen)
                  </span>
                  <span className="text-[10px] text-muted group-open:rotate-180 transition-transform">▼</span>
                </summary>
                <div className="mt-2 space-y-1.5 divide-y divide-line/40 pt-1">
                  {msg.subagentTraces.map((tr, trIdx) => (
                    <div key={trIdx} className="pt-1.5 first:pt-0 flex flex-col gap-0.5">
                      <div className="flex justify-between items-center">
                        <span className="font-bold text-textMain flex items-center gap-1">
                          <span>{tr.subagent?.icon}</span>
                          <span>{tr.subagent?.name}</span>
                        </span>
                        <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${tr.status === 'HEALTHY' || tr.status === 'APPROVED' ? 'bg-green/10 text-green border border-green/30' : 'bg-amber/10 text-amber border border-amber/30'}`}>
                          {tr.status}
                        </span>
                      </div>
                      <p className="text-muted text-[10px] leading-relaxed">{tr.key_finding}</p>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        ))}
        {isTyping && (
          <div className="rounded-xl p-2.5 text-xs leading-relaxed border border-cyan/30 bg-cyan/5 text-cyan mr-4 w-24 text-center animate-pulse flex items-center justify-center gap-1">
            <span>Menganalisa</span>
            <span>● ● ●</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompt Chips */}
      <div className="flex items-center gap-1.5 flex-wrap mb-2">
        {quickPrompts.map((chip, cIdx) => (
          <button
            key={cIdx}
            type="button"
            onClick={() => sendMessage(chip)}
            className="text-[10px] px-2 py-0.5 rounded-full bg-panel2 border border-line text-muted hover:border-cyan hover:text-cyan transition-colors"
          >
            {chip}
          </button>
        ))}
      </div>

      {/* Attached File Preview Bar before sending */}
      {attachedFile && (
        <div className="mb-2 p-2 rounded-lg bg-panel2 border border-cyan/40 flex items-center justify-between text-xs text-textMain animate-fade-in">
          <div className="flex items-center gap-2 truncate">
            <span className="text-cyan">📄</span>
            <span className="font-semibold truncate text-[11px]">{attachedFile.name}</span>
            <span className="text-[10px] text-muted font-mono">({(attachedFile.size / 1024).toFixed(1)} KB)</span>
          </div>
          <button 
            type="button"
            onClick={removeAttachedFile}
            className="h-5 w-5 rounded-full bg-red/10 text-red border border-red/30 flex items-center justify-center text-[10px] hover:bg-red/20 transition-colors ml-2"
            title="Hapus lampiran"
          >
            ✕
          </button>
        </div>
      )}

      {/* Hidden File Input */}
      <input 
        type="file" 
        ref={fileInputRef}
        onChange={handleFileSelect}
        accept=".pdf,.docx,.docm,.xlsx,.xls,.csv,.txt,.json,.md,.png,.jpg,.jpeg"
        className="hidden" 
      />

      {/* Input Form with Live Voice Microphone & Attachment Buttons */}
      <form onSubmit={handleSubmit} className="mt-auto grid grid-cols-[auto_auto_1fr_auto] gap-1.5 items-center">
        {/* Live Mic Button */}
        <button
          type="button"
          onClick={toggleListening}
          className={`h-9 w-9 rounded-lg border flex items-center justify-center text-sm transition-all ${
            isListening 
              ? 'border-red bg-red/20 text-red animate-pulse shadow-[0_0_10px_rgba(239,68,68,0.5)]' 
              : 'border-line bg-panel2 text-muted hover:text-cyan hover:border-cyan'
          }`}
          title={isListening ? 'Hentikan Rekaman Suara' : 'Bicara Sekarang (Live Mic STT)'}
        >
          {isListening ? '⏹️' : '🎙️'}
        </button>

        {/* Attachment Button */}
        <button
          type="button"
          onClick={() => fileInputRef.current && fileInputRef.current.click()}
          className="h-9 w-9 rounded-lg border border-line bg-panel2 text-muted hover:text-cyan hover:border-cyan transition-colors flex items-center justify-center text-sm"
          title="Lampirkan Dokumen/Laporan (PDF, Word, Excel, TXT, Gambar)"
        >
          📎
        </button>

        {/* Text Input */}
        <input 
          type="text" 
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          placeholder={isListening ? "Mendengarkan suara..." : (attachedFile ? "Beri instruksi untuk dokumen..." : "Ketik atau bicara langsung...")}
          className={`bg-panel2 border rounded-lg text-textMain h-9 px-3 outline-none text-xs w-full transition-colors ${isListening ? 'border-cyan animate-pulse' : 'border-line focus:border-cyan'}`}
        />

        {/* Send Button */}
        <button 
          type="submit" 
          disabled={isTyping || (!chatInput.trim() && !attachedFile)} 
          className="px-3 h-9 rounded-lg border border-cyan bg-cyan/20 text-cyan hover:bg-cyan/30 transition-colors disabled:opacity-40 text-xs font-bold"
        >
          Kirim
        </button>
      </form>
    </div>
  );
}
