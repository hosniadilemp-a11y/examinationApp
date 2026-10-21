import io
import csv
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import User, Group, Module
from backend.app.schemas import CSVImportResponse
from backend.app.security import hash_password
from backend.app.dependencies import require_admin, require_teacher_or_admin

router = APIRouter(prefix="/api/admin/csv", tags=["Imports et Exports CSV"])

def _decode_csv_content(file: UploadFile) -> csv.DictReader:
    try:
        content = file.file.read()
        # Détection d'encodage UTF-8 ou Latin-1
        try:
            text = content.decode("utf-8-sig")  # Gère le BOM Excel
        except UnicodeDecodeError:
            text = content.decode("latin-1")
            
        # Détection automatique du délimiteur (point-virgule ';' ou virgule ',')
        first_line = ""
        for line in text.splitlines():
            line_s = line.strip()
            if line_s:
                first_line = line_s
                break
        
        delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
        csv_file = io.StringIO(text)
        reader = csv.DictReader(csv_file, delimiter=delimiter)
        if not reader.fieldnames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fichier CSV vide ou format d'en-tête invalide."
            )
        # Normalisation des en-têtes (minuscules, sans espaces)
        reader.fieldnames = [fn.strip().lower() for fn in reader.fieldnames if fn]
        return reader
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur de lecture du fichier CSV : {str(e)}"
        )

@router.post("/import/students", response_model=CSVImportResponse)
def import_students_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Importe en masse les étudiants depuis un fichier CSV."""
    reader = _decode_csv_content(file)
    
    imported_count = 0
    updated_count = 0
    errors: List[str] = []
    
    row_num = 1
    for row in reader:
        row_num += 1
        try:
            student_id = row.get("student_id") or row.get("id") or row.get("matricule")
            if not student_id or not student_id.strip():
                errors.append(f"Ligne {row_num}: Colonne 'student_id' obligatoire manquante.")
                continue
                
            student_id = student_id.strip()
            username = (row.get("username") or student_id).strip()
            full_name = (row.get("full_name") or row.get("nom") or f"Étudiant {student_id}").strip()
            email = (row.get("email") or "").strip() or None
            group_id = (row.get("specialite") or row.get("specialité") or row.get("speciality") or row.get("group_id") or row.get("groupe") or "").strip()
            group_name = (row.get("group_name") or row.get("nom_specialite") or group_id).strip()
            plain_pwd = (row.get("password") or row.get("mot_de_passe") or student_id).strip()
            enrollment_year = (row.get("annee") or row.get("année") or row.get("annee_inscription") or row.get("promotion") or row.get("enrollment_year") or "").strip() or None
            
            # Gestion automatique de la création du Groupe/Spécialité si renseigné
            if group_id:
                group = db.query(Group).filter(Group.id == group_id).first()
                if not group:
                    group = Group(id=group_id, name=group_name if group_name else group_id)
                    db.add(group)
                    db.flush()
            
            # Recherche de l'étudiant existant
            existing_user = db.query(User).filter(
                (User.id == student_id) | (User.username == username)
            ).first()
            
            if existing_user:
                # Mise à jour des coordonnées
                existing_user.full_name = full_name
                if email:
                    existing_user.email = email
                if group_id:
                    existing_user.group_id = group_id
                if enrollment_year:
                    existing_user.enrollment_year = enrollment_year
                if "password" in row or "mot_de_passe" in row:
                    existing_user.password_hash = hash_password(plain_pwd)
                    existing_user.plain_password = plain_pwd
                updated_count += 1
            else:
                # Création de l'étudiant
                new_student = User(
                    id=student_id,
                    username=username,
                    password_hash=hash_password(plain_pwd),
                    plain_password=plain_pwd,
                    full_name=full_name,
                    email=email,
                    role="student",
                    group_id=group_id if group_id else None,
                    enrollment_year=enrollment_year,
                    must_change_password=False if ("password" in row or "mot_de_passe" in row) else True,
                    is_active=True
                )
                db.add(new_student)
                imported_count += 1
                
        except Exception as e:
            errors.append(f"Ligne {row_num}: Erreur de traitement ({str(e)})")
            
    db.commit()
    return CSVImportResponse(
        success=len(errors) == 0,
        imported_count=imported_count,
        updated_count=updated_count,
        errors=errors,
        message=f"{imported_count} étudiant(s) importé(s), {updated_count} mis à jour."
    )

@router.post("/import/teachers", response_model=CSVImportResponse)
def import_teachers_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Importe en masse les enseignants depuis un fichier CSV."""
    reader = _decode_csv_content(file)
    
    imported_count = 0
    updated_count = 0
    errors: List[str] = []
    
    row_num = 1
    for row in reader:
        row_num += 1
        try:
            teacher_id = row.get("teacher_id") or row.get("id")
            if not teacher_id or not teacher_id.strip():
                errors.append(f"Ligne {row_num}: 'teacher_id' manquant.")
                continue
                
            teacher_id = teacher_id.strip()
            username = (row.get("username") or teacher_id).strip()
            full_name = (row.get("full_name") or f"Enseignant {teacher_id}").strip()
            email = (row.get("email") or "").strip() or None
            assigned_modules_raw = row.get("assigned_modules") or row.get("modules") or ""
            
            existing = db.query(User).filter(
                (User.id == teacher_id) | (User.username == username)
            ).first()
            
            if existing:
                existing.full_name = full_name
                if email:
                    existing.email = email
                existing.role = "teacher"
                target_teacher = existing
                updated_count += 1
            else:
                target_teacher = User(
                    id=teacher_id,
                    username=username,
                    password_hash=hash_password(teacher_id),
                    full_name=full_name,
                    email=email,
                    role="teacher",
                    must_change_password=True,
                    is_active=True
                )
                db.add(target_teacher)
                imported_count += 1
            
            db.flush()
            
            # Affectation des modules listés (ex: "PYTHON_INIT,CRYPTO")
            if assigned_modules_raw:
                module_codes = [m.strip().upper() for m in assigned_modules_raw.split(",") if m.strip()]
                for m_code in module_codes:
                    mod = db.query(Module).filter(Module.code == m_code).first()
                    if mod and mod not in target_teacher.assigned_modules:
                        target_teacher.assigned_modules.append(mod)
                        
        except Exception as e:
            errors.append(f"Ligne {row_num}: {str(e)}")
            
    db.commit()
    return CSVImportResponse(
        success=len(errors) == 0,
        imported_count=imported_count,
        updated_count=updated_count,
        errors=errors,
        message=f"{imported_count} enseignant(s) importé(s), {updated_count} mis à jour."
    )

@router.post("/import/groups", response_model=CSVImportResponse)
def import_groups_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Importe des groupes académiques depuis un CSV."""
    reader = _decode_csv_content(file)
    imported = 0
    updated = 0
    errors = []
    row_num = 1
    
    for row in reader:
        row_num += 1
        group_id = (row.get("group_id") or row.get("id") or "").strip()
        name = (row.get("group_name") or row.get("name") or group_id).strip()
        description = (row.get("description") or "").strip() or None
        
        if not group_id:
            errors.append(f"Ligne {row_num}: 'group_id' manquant.")
            continue
            
        group = db.query(Group).filter(Group.id == group_id).first()
        if group:
            group.name = name
            group.description = description
            updated += 1
        else:
            group = Group(id=group_id, name=name, description=description)
            db.add(group)
            imported += 1
            
    db.commit()
    return CSVImportResponse(
        success=len(errors) == 0,
        imported_count=imported,
        updated_count=updated,
        errors=errors,
        message=f"{imported} groupe(s) créé(s), {updated} mis à jour."
    )

@router.post("/import/modules", response_model=CSVImportResponse)
def import_modules_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Importe des modules académiques depuis un CSV."""
    reader = _decode_csv_content(file)
    imported = 0
    updated = 0
    errors = []
    row_num = 1
    
    for row in reader:
        row_num += 1
        code = (row.get("module_code") or row.get("code") or "").strip().upper()
        title = (row.get("module_name") or row.get("title") or code).strip()
        description = (row.get("description") or "").strip() or None
        
        if not code:
            errors.append(f"Ligne {row_num}: 'module_code' manquant.")
            continue
            
        mod = db.query(Module).filter(Module.code == code).first()
        if mod:
            mod.title = title
            mod.description = description
            updated += 1
        else:
            mod = Module(code=code, title=title, description=description)
            db.add(mod)
            imported += 1
            
    db.commit()
    return CSVImportResponse(
        success=len(errors) == 0,
        imported_count=imported,
        updated_count=updated,
        errors=errors,
        message=f"{imported} module(s) créé(s), {updated} mis à jour."
    )

@router.get("/export/students")
def export_students_csv(
    enrollment_year: Optional[str] = None,
    group_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Exporte la liste des étudiants au format CSV avec filtres promotion et groupe."""
    query = db.query(User).filter(User.role == "student")
    if enrollment_year:
        query = query.filter(User.enrollment_year == enrollment_year)
    if group_id:
        query = query.filter(User.group_id == group_id)
    students = query.order_by(User.enrollment_year.desc(), User.group_id, User.username).all()
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["student_id", "username", "full_name", "email", "group_id", "enrollment_year", "must_change_password", "is_active"])
    
    for s in students:
        writer.writerow([s.id, s.username, s.full_name, s.email or "", s.group_id or "", s.enrollment_year or "", s.must_change_password, s.is_active])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=etudiants.csv"}
    )

@router.get("/export/teachers")
def export_teachers_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Exporte la liste des enseignants et leurs modules affectés au format CSV."""
    teachers = db.query(User).filter(User.role == "teacher").all()
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["teacher_id", "username", "full_name", "email", "assigned_modules"])
    
    for t in teachers:
        mods = ",".join([m.code for m in t.assigned_modules])
        writer.writerow([t.id, t.username, t.full_name, t.email or "", mods])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=enseignants.csv"}
    )

@router.get("/export/practice-level-tests")
def export_practice_level_tests_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Exporte les résultats et niveaux des 4 tests fondamentaux pour l'ensemble des étudiants.
    Inclut pour chaque étudiant les 4 piliers fondamentaux avec tentatives, 4 dernières notes,
    moyenne des 4 dernières tentatives (/20), niveau et titre de niveau,
    ainsi que la moyenne globale et le niveau global.
    """
    from backend.app.routers.practice import _compute_module_stats

    students = db.query(User).filter(User.role == "student").order_by(User.group_id, User.username).all()
    
    output = io.StringIO()
    # UTF-8 BOM pour ouverture directe sans corruption d'accents sous Microsoft Excel
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";")
    
    headers = [
        "student_id", "username", "full_name", "group_id",
        "algo_attempts", "algo_last_4_scores", "algo_last_4_avg", "algo_level", "algo_level_title",
        "python_attempts", "python_last_4_scores", "python_last_4_avg", "python_level", "python_level_title",
        "crypto_attempts", "crypto_last_4_scores", "crypto_last_4_avg", "crypto_level", "crypto_level_title",
        "linux_attempts", "linux_last_4_scores", "linux_last_4_avg", "linux_level", "linux_level_title",
        "overall_4_pillars_avg", "overall_level", "overall_level_title"
    ]
    writer.writerow(headers)
    
    for s in students:
        stats = _compute_module_stats(s.id, db)
        mods = stats.get("modules", {})
        
        algo = mods.get("ALGO", {})
        py = mods.get("PYTHON_INIT", {})
        cry = mods.get("CRYPTO", {})
        lin = mods.get("LINUX_ADMIN", {})
        
        row = [
            s.id,
            s.username,
            s.full_name,
            s.group_id or "",
            
            algo.get("attempts_count", 0),
            " | ".join(str(sc) for sc in algo.get("last_4_scores", [])),
            f"{algo.get('last_4_average', 0.0):.2f}",
            algo.get("level", 1),
            algo.get("level_title", "Niveau 1"),
            
            py.get("attempts_count", 0),
            " | ".join(str(sc) for sc in py.get("last_4_scores", [])),
            f"{py.get('last_4_average', 0.0):.2f}",
            py.get("level", 1),
            py.get("level_title", "Niveau 1"),
            
            cry.get("attempts_count", 0),
            " | ".join(str(sc) for sc in cry.get("last_4_scores", [])),
            f"{cry.get('last_4_average', 0.0):.2f}",
            cry.get("level", 1),
            cry.get("level_title", "Niveau 1"),
            
            lin.get("attempts_count", 0),
            " | ".join(str(sc) for sc in lin.get("last_4_scores", [])),
            f"{lin.get('last_4_average', 0.0):.2f}",
            lin.get("level", 1),
            lin.get("level_title", "Niveau 1"),
            
            f"{stats.get('overall_last_4_average', 0.0):.2f}",
            stats.get("overall_level", 1),
            stats.get("overall_level_title", "Grand Débutant (Niveau 1)")
        ]
        writer.writerow(row)
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=resultats_tests_de_niveau_4_piliers.csv"}
    )
