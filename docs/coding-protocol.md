# Protokol Coding PPLE Agent

Status: standar normatif untuk manusia dan coding agent  
Kata kunci: **WAJIB**, **DILARANG**, **SEBAIKNYA**, dan **BOLEH** mengikuti arti RFC 2119 secara praktis.

## 1. Prinsip yang tidak boleh dilanggar

1. Rule-based engineering adalah sumber kebenaran. LLM hanya memperkaya penjelasan dan WAJIB memiliki fallback lokal.
2. UI, API, dan CLI DILARANG menduplikasi threshold, health status, fusion, atau safety rule.
3. Perubahan kecil dan dapat dibuktikan lebih disukai daripada rewrite besar.
4. Data yang tidak tersedia adalah `unknown/data gap`, bukan bukti kondisi normal.
5. Tindakan berisiko tinggi tetap melewati `SafetyGuardrailAgent` dan otorisasi manusia.
6. Perubahan yang sudah ada di worktree dan tidak terkait DILARANG diubah atau dihapus.

## 2. Protokol sebelum coding

Setiap perubahan WAJIB dimulai dengan:

1. Baca `README.md`, `AGENTS.md`, file target, caller, dan test terdekat.
2. Jalankan `git status --short` dan catat perubahan yang bukan milik pekerjaan saat ini.
3. Nyatakan contract yang berubah: input, output, side effect, error, dan compatibility.
4. Pilih test terkecil yang membuktikan behavior.
5. Untuk bug/behavior change, tulis test yang gagal terlebih dahulu dan pastikan alasan gagalnya benar.
6. Jika menyentuh data engineering, identifikasi unit, equipment, timestamp, unit pengukuran, source, dan quality flag.

Perubahan tidak boleh dimulai dari “rapikan semua”. Harus ada scope yang dapat ditinjau dalam satu PR.

## 3. Batas dependency

### Domain dan application

- Domain DILARANG mengimpor `streamlit`, `fastapi`, React payload, atau object HTTP.
- Domain DILARANG membaca environment variable atau file secara tersembunyi; nilai masuk melalui parameter/adapter.
- Kalkulasi WAJIB pure/deterministic bila memungkinkan.
- Nilai teknik WAJIB menyimpan unit eksplisit pada nama/schema bila tipe unit belum tersedia, misalnya `overall_rms_mm_s`.
- Hasil diagnosis WAJIB menyertakan evidence, confidence, source/provenance, dan `next_data_needed` bila bukti kurang.
- Application use case mengorkestrasi domain dan port; tidak merender UI atau membentuk response HTTP.

### Infrastructure

- Akses CSV/Excel/JSON/SQLite/FAISS/provider LLM berada di adapter infrastructure atau modul data legacy yang ditetapkan.
- Semua write data WAJIB atomic bila memungkinkan, membuat backup sesuai kebijakan, dan mencatat audit/provenance.
- Path WAJIB diselesaikan melalui helper repo (`get_data_path` atau adapter terkait), bukan relative path tersebar.
- Optional dependency WAJIB gagal dengan pesan jelas dan fallback yang sudah diuji.

### Delivery

- FastAPI router hanya: validasi, panggil use case, mapping response, mapping error.
- Streamlit page hanya: widget/layout, panggil use case, tampilkan view model.
- React component hanya: interaction/rendering; request dipusatkan pada feature API/hook.
- CLI hanya: parse argument, confirmation/safety, panggil use case, format output.

## 4. Kontrak API

Setiap endpoint baru atau berubah WAJIB memiliki:

- Pydantic request dan response model;
- tipe serta batas nilai yang eksplisit;
- error envelope konsisten: `code`, `message`, `details`, `request_id`;
- auth policy eksplisit;
- test success, invalid input, not found, unauthorized bila relevan, dan domain failure;
- compatibility note bila mengubah field publik.

Aturan response:

- Timestamp menggunakan ISO 8601 dengan timezone.
- Status memakai enum kanonik, bukan string bebas.
- Empty list adalah `[]`, bukan `null`, kecuali `null` memang bermakna unknown.
- Field lama tidak dihapus dalam PR yang sama dengan pengenalan penggantinya.
- Endpoint DILARANG mengembalikan traceback, API key, path internal sensitif, atau dataframe mentah tanpa schema.

Frontend WAJIB memeriksa `response.ok`. Error tidak boleh hanya masuk `console.error`; UI harus memiliki pesan yang dapat ditindaklanjuti dan tombol retry bila operasi aman diulang.

## 5. Standar Python

- Gunakan type hint pada API publik dan fungsi domain.
- Gunakan dataclass/Pydantic model untuk kontrak stabil; hindari dict bertingkat tanpa schema.
- Satu fungsi memiliki satu tujuan; target sekitar 60 baris, ekstrak bila branching sulit dibaca.
- Tangkap exception spesifik. `except BaseException` hanya boleh pada fatal bootstrap boundary yang memang harus menangkap kegagalan import.
- DILARANG menelan exception tanpa log/context.
- Nama fungsi berbentuk aksi (`load_`, `evaluate_`, `build_`); boolean memakai `is_`, `has_`, atau `should_`.
- User-facing text menggunakan Bahasa Indonesia; identifier kode menggunakan English yang konsisten dengan domain.
- Hindari mutable module global untuk state per user/request.

Import direction yang diharapkan:

```text
delivery -> application -> domain
                       -> ports <- infrastructure
```

Jika import melawan arah ini, PR WAJIB menjelaskan alasan dan rencana pelepasannya.

## 6. Standar Streamlit

- `app.py` hanya bootstrap/navigation; business logic DILARANG ditambahkan ke entry point.
- Page baru memakai `st.Page` dan SEBAIKNYA berupa direct page script di `app_pages/`.
- State lintas halaman diinisialisasi satu kali; state fitur memakai prefix stabil.
- Widget dinamis/repeated WAJIB mempunyai `key` stabil.
- Loader mahal memakai `st.cache_data`; resource bersama memakai `st.cache_resource`. Cache parameterized WAJIB punya TTL atau `max_entries` yang masuk akal.
- Filter murah dilakukan setelah source data cache.
- Gunakan `st.form` untuk input yang dieksekusi sebagai satu transaksi.
- Gunakan `st.fragment` hanya untuk bagian independen; jangan menulis state bersama tanpa disiplin.
- Tabs/expander dengan pekerjaan mahal WAJIB mempunyai conditional gating.
- Gunakan native Streamlit dan `.streamlit/config.toml` lebih dahulu.
- `unsafe_allow_html=True` membutuhkan alasan dalam code comment dan regression check visual/manual.
- Gunakan `width="stretch"`/`width="content"`; DILARANG menambah `use_container_width` baru.
- Ikon memakai Material Symbols. Emoji bukan ikon kontrol.

## 7. Standar React

- Component menggunakan functional component dan hooks.
- Data fetching berada di feature hook/service, bukan disalin pada beberapa component.
- Request independen dijalankan paralel; hindari waterfall yang tidak diperlukan.
- Route workspace berat SEBAIKNYA lazy-loaded.
- Jangan membuat component di dalam component.
- Derived state dihitung saat render; jangan menyimpan duplikatnya lewat effect.
- `useEffect` hanya untuk sinkronisasi dengan sistem eksternal, bukan event handler terselubung.
- List memakai key identitas domain, bukan index, bila urutan dapat berubah.
- Optimasi `memo`/`useMemo` dilakukan setelah profiling atau ada perhitungan mahal yang jelas.
- Import komponen berat secara langsung; hindari barrel import yang memperlebar bundle.
- Semua halaman data WAJIB memiliki loading, empty, error, dan stale/last-updated state.
- Interactive element WAJIB dapat dipakai keyboard dan memiliki accessible name.

## 8. Standar UI/UX dan design token

Gunakan semantic token; raw hex di page/component DILARANG kecuali visualisasi data dinamis yang terdokumentasi.

| Token | Makna |
| --- | --- |
| `action` | aksi utama, selection, link |
| `healthy` | kondisi normal tervalidasi |
| `watch` | perlu dipantau |
| `warning` | investigasi terjadwal |
| `alert` | tindakan prioritas |
| `critical` | risiko tinggi/mitigasi segera |
| `unknown` | data tidak ada/tidak cukup |
| `surface`, `surface-muted`, `border` | struktur tampilan |
| `text`, `text-muted`, `focus` | keterbacaan dan navigasi |

Aturan visual:

- Warna tidak boleh menjadi satu-satunya pembeda status.
- Contrast text minimal 4.5:1; text besar minimal 3:1.
- Focus ring tidak boleh dihapus.
- Target sentuh utama minimal 44 x 44 px dengan jarak minimal 8 px.
- Label form selalu terlihat atau tetap tersedia bagi screen reader.
- Body text penting minimal 14 px pada dashboard; teks baca panjang 16 px dengan line-height sekitar 1.5.
- Loading memberikan feedback; submit menampilkan success/error di dekat konteks aksi.
- Animasi hanya menjelaskan perubahan state, 150-250 ms, dan menghormati reduced motion.
- Chart menampilkan title, unit, legend/label, tooltip, source, timestamp, dan state no-data.
- “Live/online” hanya dipakai bila ada sumber health/heartbeat aktual.

## 9. Data dan CBM safety

- Jangan mengubah threshold tanpa sumber, unit, effective date, dan test boundary.
- Test threshold minimal mencakup tepat di bawah, tepat pada, dan tepat di atas batas.
- Normalisasi equipment dilakukan oleh helper kanonik, bukan regex lokal baru di UI.
- Filter asset harus ketat; permintaan asset yang tidak cocok DILARANG menganalisis sample asset lain.
- Waktu sampling, timezone, dan freshness WAJIB dipertahankan sampai hasil akhir.
- Sample default/synthetic harus ditandai jelas dan tidak boleh masuk fleet health produksi tanpa flag.
- Fusion hanya memakai modality yang benar-benar tersedia; confidence turun saat coverage berkurang.
- LLM tidak boleh membuat angka pengukuran, threshold, citation, atau status engineering baru.

## 10. Test matrix

| Perubahan | Minimal gate |
| --- | --- |
| Rule/domain Python | test unit spesifik + regression/characterization terkait |
| FastAPI contract | test unit domain + `tests.test_api_server` atau test router terkait |
| Streamlit UI | test helper/view model + `tests.test_streamlit_app` + smoke manual halaman |
| React component/API state | lint + build + test interaction/contract setelah test runner tersedia |
| Data ingest/write | preview/validation test + backup/audit test + functional verification |
| Knowledge base | retriever/processor test + force reload behavior |
| LLM/RAG opsional | offline/fallback test; live test boleh skip tanpa key/dependency |
| Report | unit generator terkait + buka artefak hasil secara manual bila layout berubah |

Gate sebelum menyatakan selesai:

```powershell
python -m unittest discover -s . -p "test_*.py"
python verify_app.py
npm --prefix frontend run lint
npm --prefix frontend run build
```

Jalankan subset terlebih dahulu, lalu full gate sesuai risiko. Test repo memakai `unittest`, bukan pytest.

## 11. Ukuran PR dan review

Satu PR SEBAIKNYA memiliki satu tujuan behavior. Refactor dan perubahan behavior dipisah bila reviewer tidak dapat membuktikan keduanya sekaligus.

Checklist reviewer:

- [ ] Scope dan alasan perubahan jelas.
- [ ] Tidak ada user change yang ikut tertimpa.
- [ ] Dependency mengikuti arah arsitektur.
- [ ] Tidak ada rule/threshold baru di UI/API.
- [ ] Kontrak serta compatibility dinyatakan.
- [ ] Test membuktikan behavior dan boundary.
- [ ] Loading/error/empty/accessibility diperiksa untuk perubahan UI.
- [ ] Data provenance, unit, dan timestamp dipertahankan.
- [ ] LLM tetap optional dan fallback lulus.
- [ ] Safety guard tidak memiliki bypass.
- [ ] Dokumentasi/ADR diperbarui bila keputusan bersifat lintas modul.

## 12. Definition of done

Pekerjaan baru selesai bila:

1. Behavior sesuai acceptance criteria dan test relevan lulus.
2. `python verify_app.py` lulus sebelum klaim completion, kecuali blocker eksternal dijelaskan.
3. Tidak ada secret, data sensitif, atau artefak build yang ikut commit.
4. Observability cukup untuk memahami failure tanpa membuka debugger.
5. Dokumentasi pengguna/kontrak diperbarui bila perilaku publik berubah.
6. Risiko sisa, test yang tidak dijalankan, dan perubahan worktree yang tidak disentuh dilaporkan.

## 13. Kapan ADR wajib dibuat

Buat ADR di `docs/adr/` bila perubahan:

- mengganti sumber kebenaran data atau diagnosis;
- menambah dependency/framework utama;
- mengubah batas Streamlit/React/API/CLI;
- mengubah schema publik atau format penyimpanan;
- mengubah safety policy, auth, audit, atau retention;
- memperkenalkan background process/service baru.

ADR minimal berisi context, decision, alternatives, consequences, migration, dan rollback.

