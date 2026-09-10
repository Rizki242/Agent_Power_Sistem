# Feature Parity Streamlit dan React

Status: baseline fase 0  
Tujuan: mencegah dua UI mengembangkan business rule yang berbeda.

## Arti status

- **Canonical**: UI utama untuk workflow tersebut.
- **Supported**: UI pendamping; behavior bisnis harus memakai contract/use case yang sama.
- **Not planned**: tidak perlu diparitas-kan kecuali ada keputusan produk baru.
- **Placeholder**: navigasi tersedia, workflow belum lengkap.

## Matrix

| Capability | Streamlit | React | Sumber logic/contract | Keputusan |
| --- | --- | --- | --- | --- |
| Fleet command center | Agent Dashboard | Dashboard | fleet reliability + FastAPI summary | React canonical; Streamlit supported |
| MCSA engineering analysis | MCSA | MCSA Workspace | `src` rule-based MCSA, API | Streamlit canonical sampai seluruh detail tervalidasi di React |
| Vibration analysis | Vibrasi | Vibration Workspace | `src.vibration_data`, specialist agent | Streamlit canonical; React supported |
| DGA analysis | DGA | DGA Workspace | `src.dga_data`, specialist router | Streamlit canonical; React supported |
| Tribology analysis | Tribology | Tribology Workspace | `src.tribology_data`, specialist router | Streamlit canonical; React supported |
| Thermal analysis | Thermal | Thermal Workspace | `src.thermal_data`, specialist router | Streamlit canonical; React supported |
| Partial discharge | Partial Discharge | PD Workspace | `src.pd_data`, specialist router | Streamlit canonical; React supported; disclaimer data wajib |
| Reliability fusion | Agent Dashboard | Reliability Command Center | shared fusion engine/API | React canonical; Streamlit supported |
| Asset hierarchy/health | Register Aset + dashboard | Asset Health + sidebar tree | asset registry/API | React canonical untuk eksplorasi; Streamlit canonical untuk edit |
| Data management | Manajemen Data | Belum ada workflow penuh | `src.data_loader` | Streamlit canonical; React not planned |
| Word batch sync dan QC | Sync + Quality Check | Belum ada | report batch application logic | Streamlit canonical; React not planned |
| Knowledge search/read | Materi Training | Knowledge Workspace | keyword/RAG API | Supported pada keduanya |
| Knowledge upload/delete | Materi Training edit mode | Belum lengkap | knowledge processor/API | Streamlit canonical |
| Report PPT/Word | Laporan PPT/Word | Report access terbatas | report generators/API | Streamlit canonical |
| Work order | Placeholder | Work Order Center | work-order API/store | React canonical; Streamlit placeholder |
| Settings AI/provider | Settings | Belum setara | shared settings/provider config | Streamlit canonical |
| Chat assistant | Chatbot | AI Chat Panel | rule answer + optional LLM | Supported pada keduanya; fallback wajib identik |
| Digital twin | Tidak ada | Digital Twin Workspace | belum menjadi core workflow | React experimental |
| CLI engineering/status | N/A | N/A | `pple` application/domain | CLI canonical untuk automation |

## Aturan perubahan parity

1. PR yang menambah fitur UI WAJIB memperbarui matrix ini bila ownership berubah.
2. UI `supported` tidak boleh membuat threshold atau status sendiri; gunakan API/use case canonical.
3. Perbedaan presentasi diperbolehkan, perbedaan hasil diagnosis tidak.
4. Workflow `not planned` tidak menjadi blocker parity release.
5. Placeholder harus diberi label jelas dan tidak boleh memberi kesan workflow sudah operasional.
6. Data illustrative/synthetic harus menampilkan disclaimer pada kedua UI.

## Contract minimum untuk fitur supported

- input asset, unit, tanggal, dan unit pengukuran sama;
- status enum dan severity mapping sama;
- evidence, confidence, provenance, dan timestamp tersedia;
- empty, unknown, stale, dan provider failure tidak diubah menjadi status normal;
- safety decision dan work-order approval tetap memerlukan jalur otorisasi yang sama.

