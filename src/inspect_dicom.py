"""
À lancer AVANT build_dataset.py sur un nouvel export DICOM : liste les 4DCT
détectés, leurs phases et leur nombre de coupes, sans rien écrire.

Si une phase manque, c'est généralement que la description de série ne
contient pas de pourcentage (ex. « Gated, 50.0% ») : adapter alors PHASE_RE
dans io4d.py au format du constructeur.

Usage : python inspect_dicom.py /chemin/export_dicom
"""
import sys

from io4d import scan_dicom_folder

groups = scan_dicom_folder(sys.argv[1], verbose=True)
if not groups:
    print("Aucune série gatée trouvée (pas de '%' dans SeriesDescription ?).")
for (pid, key), by_phase in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
    phases = sorted(by_phase)
    counts = {int(p): len(by_phase[p]) for p in phases}
    print(f"Patient {pid} | étude {key[0][-12:]} | date {key[2]} | {len(phases)} phases")
    print(f"   coupes par phase : {counts}")
