# 📝 Git Cheat-Sheet (Basics)

### 1. Status prüfen
```bash
git status
```
➡️ Zeigt, ob Dateien geändert, neu oder gelöscht wurden. Dein „Kontrollzentrum“.

---

### 2. Änderungen sichern
```bash
git add <datei>         # bestimmte Datei
git add .               # alle Änderungen
git commit -m "Kurze Nachricht"
```
➡️ Speichert deine Änderungen dauerhaft im Repo.

---

### 3. Branches
```bash
git branch              # alle Branches anzeigen
git checkout -b <name>  # neuen Branch erstellen und wechseln
git checkout <name>     # zu existierendem Branch wechseln
```
➡️ Branches = parallele Arbeitsstände, ohne „main“ kaputt zu machen.

---

### 4. Unterschiede ansehen
```bash
git diff                # Unterschiede seit letztem Commit
git log --oneline --graph --decorate --all
```
➡️ Diff = was sich geändert hat,
Log = hübscher Überblick über deine Historie mit Branches.

---

### 5. Branches zusammenführen
```bash
git checkout main
git merge context-debug-20250902 -m "Merge context debug features"
```
➡️ Bringt Änderungen von deinem Feature-Branch zurück in den Hauptzweig.

---

⚡ Bonus: Änderungen rückgängig machen
```bash
git restore <datei>              # lokale Änderung verwerfen
git reset --soft HEAD~1          # letzten Commit rückgängig (Änderungen bleiben)
git reset --hard HEAD~1          # letzten Commit + Änderungen komplett weg!
```
