from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response, current_app
from flask_login import login_required, current_user
from app.models.vacances import DemandeVacances
from app import db, csrf
from datetime import datetime
from app.routes.auth import role_required
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from io import BytesIO
import os
import base64
import tempfile

bp = Blueprint('vacances', __name__)

@bp.route('/vacances')
@login_required
def liste_vacances():
    demandes = DemandeVacances.query.order_by(DemandeVacances.date_creation.desc()).all()
    return render_template('vacances/liste_vacances.html', demandes=demandes)

@csrf.exempt
@bp.route('/vacances/nouvelle', methods=['GET', 'POST'])
@login_required
def nouvelle_demande():
    if request.method == 'POST':
        try:
            # Print form data for debugging
            print("Form data received:", request.form)
            
            # Validate required fields
            required_fields = ['unite', 'type_vacances', 'nom_prenom', 'emploi', 
                             'nombre_jours', 'date_sortie', 'date_entree', 
                             'lieu_residence', 'residuel', 'annee_en_cours', 'total']
            
            for field in required_fields:
                if field not in request.form or not request.form[field]:
                    raise ValueError(f"Le champ {field} est requis")

            # Get exercise year from form, default to None if not provided
            annee_exercice = request.form.get('annee_exercice', '').strip()
            if annee_exercice:
                try:
                    annee_exercice = int(annee_exercice)
                except ValueError:
                    annee_exercice = None
            else:
                annee_exercice = None

            # Convert decimal string values to float first, then round to 1 decimal place
            try:
                nombre_jours = round(float(request.form['nombre_jours']), 1)
                residuel = round(float(request.form['residuel']), 1)
                annee_en_cours = round(float(request.form['annee_en_cours']), 1)
                total = round(float(request.form['total']), 1)
                
                # Validate that nombre_jours doesn't exceed total
                if nombre_jours > total:
                    raise ValueError("Le nombre de jours demandés ne peut pas dépasser le total disponible")
                
            except ValueError as e:
                raise ValueError("Les champs numériques doivent contenir des nombres valides")

            # Create new request with explicit type conversion
            demande = DemandeVacances(
                unite=request.form['unite'].strip(),
                type_vacances=request.form['type_vacances'].strip(),
                nom_prenom=request.form['nom_prenom'].strip(),
                emploi=request.form['emploi'].strip(),
                interet=request.form.get('interet', '').strip(),
                nombre_jours=nombre_jours,
                date_sortie=datetime.strptime(request.form['date_sortie'], '%Y-%m-%d').date(),
                date_entree=datetime.strptime(request.form['date_entree'], '%Y-%m-%d').date(),
                lieu_residence=request.form['lieu_residence'].strip(),
                nom_alternatif=request.form.get('nom_alternatif', '').strip(),
                residuel=residuel,
                residuel_clarification=request.form.get('residuel_clarification', '').strip(),
                annee_exercice=annee_exercice,
                annee_en_cours=annee_en_cours,
                total=total,
                createur=current_user.username
            )
            
            db.session.add(demande)
            db.session.commit()
            flash('Demande de vacances créée avec succès!', 'success')
            return redirect(url_for('vacances.liste_vacances'))
            
        except ValueError as ve:
            db.session.rollback()
            flash(f'Erreur de validation: {str(ve)}', 'error')
            print(f"Validation error: {str(ve)}")
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la création de la demande: {str(e)}', 'error')
            print(f"Error creating request: {str(e)}")
    
    current_year = datetime.now().year
    return render_template('vacances/nouvelle_demande.html', current_year=current_year)

@bp.route('/vacances/<int:id>')
@login_required
def voir_demande(id):
    demande = DemandeVacances.query.get_or_404(id)
    return render_template('vacances/voir_demande.html', demande=demande)

@bp.route('/vacances/<int:id>/approuver')
@login_required
@role_required('DG')
def approuver_demande(id):
    demande = DemandeVacances.query.get_or_404(id)
    demande.statut = 'Approuvé'
    demande.avis_directeur_general = 'Approuvé'
    demande.signature_dg = True
    
    # Add DG signature
    signature_path = os.path.join(current_app.static_folder, 'images', 'signatures', 'manager_signature.png')
    if os.path.exists(signature_path):
        with open(signature_path, 'rb') as img_file:
            signature_data = base64.b64encode(img_file.read()).decode('utf-8')
            demande.signature_data = f'data:image/png;base64,{signature_data}'
    
    db.session.commit()
    flash('Demande de vacances approuvée!', 'success')
    return redirect(url_for('vacances.liste_vacances'))

@bp.route('/vacances/<int:id>/refuser')
@login_required
@role_required('DG')
def refuser_demande(id):
    demande = DemandeVacances.query.get_or_404(id)
    demande.statut = 'Refusé'
    demande.avis_directeur_general = 'Refusé'
    db.session.commit()
    flash('Demande de vacances refusée!', 'success')
    return redirect(url_for('vacances.liste_vacances'))

@csrf.exempt
@bp.route('/vacances/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier_demande(id):
    if current_user.role != 'DG':
        flash('Seul le directeur général peut modifier les demandes.', 'error')
        return redirect(url_for('vacances.voir_demande', id=id))
        
    demande = DemandeVacances.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Get exercise year from form, default to None if not provided
            annee_exercice = request.form.get('annee_exercice', '').strip()
            if annee_exercice:
                try:
                    annee_exercice = int(annee_exercice)
                except ValueError:
                    annee_exercice = None
            else:
                annee_exercice = None
                
            # Convert numeric fields with validation
            try:
                nombre_jours = round(float(request.form['nombre_jours']), 1)
                residuel = round(float(request.form['residuel']), 1)
                annee_en_cours = round(float(request.form['annee_en_cours']), 1)
                total = round(float(request.form['total']), 1)
                
                # Validate that nombre_jours doesn't exceed total
                if nombre_jours > total:
                    raise ValueError("Le nombre de jours demandés ne peut pas dépasser le total disponible")
                    
            except ValueError:
                raise ValueError("Les champs numériques doivent contenir des nombres valides")
                
            demande.unite = request.form['unite'].strip()
            demande.type_vacances = request.form['type_vacances'].strip()
            demande.nom_prenom = request.form['nom_prenom'].strip()
            demande.emploi = request.form['emploi'].strip()
            demande.interet = request.form.get('interet', '').strip()
            demande.nombre_jours = nombre_jours
            demande.date_sortie = datetime.strptime(request.form['date_sortie'], '%Y-%m-%d').date()
            demande.date_entree = datetime.strptime(request.form['date_entree'], '%Y-%m-%d').date()
            demande.lieu_residence = request.form['lieu_residence'].strip()
            demande.nom_alternatif = request.form.get('nom_alternatif', '').strip()
            demande.residuel = residuel
            demande.residuel_clarification = request.form.get('residuel_clarification', '').strip()
            demande.annee_exercice = annee_exercice
            demande.annee_en_cours = annee_en_cours
            demande.total = total
            
            db.session.commit()
            flash('Demande de vacances modifiée avec succès!', 'success')
            return redirect(url_for('vacances.voir_demande', id=id))
        except ValueError as ve:
            db.session.rollback()
            flash(f'Erreur de validation: {str(ve)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification: {str(e)}', 'error')
    
    return render_template('vacances/modifier_demande.html', demande=demande)

@bp.route('/vacances/<int:id>/supprimer')
@login_required
def supprimer_demande(id):
    if current_user.role != 'DG':
        flash('Seul le directeur général peut supprimer les demandes.', 'error')
        return redirect(url_for('vacances.voir_demande', id=id))
    
    try:
        demande = DemandeVacances.query.get_or_404(id)
        db.session.delete(demande)
        db.session.commit()
        flash('Demande de vacances supprimée avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression: {str(e)}', 'error')
    
    return redirect(url_for('vacances.liste_vacances'))

def create_vacation_pdf(demande, buffer):
    # Create PDF
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Logo positioning - moved further left
    logo_path = os.path.join(current_app.static_folder, 'images', 'gmi-logo.png')
    if os.path.exists(logo_path):
        c.drawImage(logo_path, 10*mm, 250*mm, width=25*mm, height=25*mm, preserveAspectRatio=True, mask='auto')

    # Header text with exact styling and adjusted positioning
    # Company name - increased space after logo
    c.setFont("Helvetica-Bold", 16)
    company_name = "EURL G.M.I ALGÉRIE"
    company_name_width = c.stringWidth(company_name, "Helvetica-Bold", 16)
    text_start_x = 45*mm  # Moved text start position more to the left
    available_width = width - (45*mm + 25*mm)  # Adjusted available width
    c.drawString(text_start_x + (available_width - company_name_width)/2, 270*mm, company_name)
    
    # Description lines - adjusted to align with company name
    c.setFont("Helvetica", 11)
    
    desc1 = "FABRICATION & MONTAGE DES ÉQUIPEMENTS ÉLECTRIQUES ET HYDRAULIQUES"
    desc1_width = c.stringWidth(desc1, "Helvetica", 11)
    c.drawString(text_start_x + (available_width - desc1_width)/2, 263*mm, desc1)
    
    desc2 = "GROUPES ÉLECTROGÈNES, GROUPES DE SOUDAGE"
    desc2_width = c.stringWidth(desc2, "Helvetica", 11)
    c.drawString(text_start_x + (available_width - desc2_width)/2, 256*mm, desc2)
    
    desc3 = "ZONE INDUSTRIEL Oued Sly W.chlef"
    desc3_width = c.stringWidth(desc3, "Helvetica", 11)
    c.drawString(text_start_x + (available_width - desc3_width)/2, 249*mm, desc3)
    
    # Contact information - adjusted to match new alignment
    contact = "Tél: 020656464 / 020656666 / Fax: 020656588"
    contact_width = c.stringWidth(contact, "Helvetica", 11)
    c.drawString(text_start_x + (available_width - contact_width)/2, 242*mm, contact)

    # Add decorative line - adjusted to match new alignment
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.5)
    c.line(20*mm, 235*mm, width-20*mm, 235*mm)

    # Title and Reference Number with better styling
    current_year = datetime.now().year
    ref_number = f"{demande.id:03d}/{current_year}"
    
    if demande.statut == 'Approuvé':
        # Add a light blue background for the title
        c.setFillColorRGB(0.9, 0.95, 1)  # Very light blue
        c.rect(30*mm, 225*mm, width-60*mm, 15*mm, fill=True)
        c.setFillColorRGB(0, 0, 0)  # Reset to black
        
        c.setFont("Helvetica-Bold", 16)
        title_text = f"TITRE DE CONGÉ N°: {ref_number}"
        title_width = c.stringWidth(title_text, "Helvetica-Bold", 16)
        c.drawString((width-title_width)/2, 230*mm, title_text)
    else:
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width/2, 230*mm, "DEMANDE DE VACANCES")

    # Main Content with improved layout
    if demande.statut == 'Approuvé':
        # Add subtle box around main content
        c.setStrokeColorRGB(0.8, 0.8, 0.8)  # Light gray
        c.roundRect(25*mm, 80*mm, width-50*mm, 130*mm, 5*mm)
        c.setStrokeColorRGB(0, 0, 0)  # Reset to black
        
        y = 190  # Adjusted starting position
        
        # Employee Information with consistent spacing and alignment
        def draw_field(label, value, y_pos):
            c.setFont("Helvetica-Bold", 11)
            c.drawString(35*mm, y_pos*mm, label)
            c.setFont("Helvetica", 11)
            return c.drawString(label.startswith("ADRESSE") and 65*mm or 95*mm, y_pos*mm, value)

        # Draw fields with consistent spacing
        draw_field("NOM ET PRENOM:", demande.nom_prenom, y)
        y -= 12
        draw_field("FONCTION:", demande.emploi, y)
        y -= 12
        # Use custom exercise year if provided, otherwise use current year
        if demande.annee_exercice:
            exercise_year = f"{demande.annee_exercice}/{demande.annee_exercice + 1}"
        else:
            exercise_year = f"{current_year-1}/{current_year}"
        draw_field("EXERCICE:", exercise_year, y)
        y -= 12
        draw_field("NOMBRE DE JOURS:", f"{demande.nombre_jours} JOURS", y)
        y -= 12
        draw_field("TYPE DE CONGÉ:", demande.type_vacances, y)
        y -= 12
        draw_field("DATE DE SORTIE:", demande.date_sortie.strftime('%d/%m/%Y'), y)
        y -= 12
        draw_field("DATE DE RETOUR:", demande.date_entree.strftime('%d/%m/%Y'), y)
        y -= 12
        
        # Period restante with clarification - Fixed calculation
        periode_restante = float(demande.total) - float(demande.nombre_jours)  # Calculate from total instead of residuel
        periode_text = f"{periode_restante:.1f} JOURS"  # Format to 1 decimal place
        if demande.residuel_clarification:
            periode_text += f" ({demande.residuel_clarification})"
        draw_field("PERIODE RESTANTE:", periode_text, y)
        y -= 12
        draw_field("ADRESSE:", demande.lieu_residence, y)
        
        # Signature section with better styling
        y -= 25
        c.setFont("Helvetica-Bold", 11)
        date_text = f"Oued Sly le: {datetime.now().strftime('%d/%m/%Y')}"
        date_width = c.stringWidth(date_text, "Helvetica-Bold", 11)
        c.drawString((width - 30*mm - date_width), y*mm, date_text)
        
        # Add subtle box around signature area
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.roundRect(width-80*mm, (y-40)*mm, 50*mm, 35*mm, 3*mm)
        c.setStrokeColorRGB(0, 0, 0)
        
        y -= 30
        c.setFont("Helvetica-Bold", 11)
        directeur_text = "Le Directeur Général"
        text_width = c.stringWidth(directeur_text, "Helvetica-Bold", 11)
        c.drawString((width - 55*mm - text_width/2), y*mm, directeur_text)

    # Add footer with subtle styling
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.line(30*mm, 25*mm, width-30*mm, 25*mm)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(35*mm, 15*mm, f"Document généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    c.drawRightString(width-35*mm, 15*mm, f"Page 1/1")

    c.save()

@bp.route('/vacances/<int:id>/pdf')
@login_required
def telecharger_pdf(id):
    try:
        demande = DemandeVacances.query.get_or_404(id)
        
        # Create PDF buffer
        buffer = BytesIO()
        
        # Generate PDF
        create_vacation_pdf(demande, buffer)
        
        # Prepare response
        buffer.seek(0)
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=demande_vacances_{id}.pdf'
        
        return response
    
    except Exception as e:
        flash(f'Erreur lors de la génération du PDF: {str(e)}', 'error')
        return redirect(url_for('vacances.voir_demande', id=id))

@bp.route('/demande/<int:id>/imprimer')
@login_required
def imprimer_demande(id):
    try:
        demande = DemandeVacances.query.get_or_404(id)
        
        # Create PDF buffer
        buffer = BytesIO()
        
        # Generate PDF
        create_vacation_pdf(demande, buffer)
        
        # Prepare response
        buffer.seek(0)
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        # For printing, we'll display inline instead of downloading
        response.headers['Content-Disposition'] = f'inline; filename=demande_vacances_{id}.pdf'
        
        return response
    
    except Exception as e:
        flash(f'Erreur lors de la génération du PDF: {str(e)}', 'error')
        return redirect(url_for('vacances.voir_demande', id=id))

@bp.route('/vacances/archive')
@login_required
def archive_vacances():
    # Get filter parameters
    year = request.args.get('year', type=int)
    status = request.args.get('status')
    type_vacances = request.args.get('type')
    search = request.args.get('search', '').strip()
    
    # Base query
    query = DemandeVacances.query
    
    # Apply filters
    if year:
        query = query.filter(
            db.or_(
                DemandeVacances.annee_exercice == year,
                DemandeVacances.annee_en_cours == float(year)  # Convert to float since annee_en_cours is float
            )
        )
    if status:
        query = query.filter(DemandeVacances.statut == status)
    if type_vacances:
        query = query.filter(DemandeVacances.type_vacances == type_vacances)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                DemandeVacances.nom_prenom.ilike(search_term),
                DemandeVacances.unite.ilike(search_term),
                DemandeVacances.emploi.ilike(search_term),
                DemandeVacances.lieu_residence.ilike(search_term),
                DemandeVacances.nom_alternatif.ilike(search_term),
                DemandeVacances.interet.ilike(search_term),
                DemandeVacances.residuel_clarification.ilike(search_term),
                DemandeVacances.type_vacances.ilike(search_term)
            )
        )
    
    # Sort by date_creation descending
    demandes = query.order_by(DemandeVacances.date_creation.desc()).all()
    
    # Get unique years for filter dropdown - ensure all values are integers
    years_exercice = db.session.query(
        db.distinct(DemandeVacances.annee_exercice)
    ).filter(
        db.and_(
            DemandeVacances.annee_exercice.isnot(None),
            DemandeVacances.annee_exercice != ''  # Exclude empty strings
        )
    ).all()
    
    years_en_cours = db.session.query(
        db.distinct(DemandeVacances.annee_en_cours)
    ).filter(
        db.and_(
            DemandeVacances.annee_en_cours.isnot(None),
            DemandeVacances.annee_en_cours != 0  # Exclude zero values
        )
    ).all()
    
    # Convert float years to integers and combine both lists
    all_years = []
    for y in years_exercice:
        if y[0] and str(y[0]).strip():  # Check if value exists and is not empty
            try:
                year_val = int(y[0])
                if year_val > 0:  # Only add positive years
                    all_years.append(year_val)
            except (ValueError, TypeError):
                continue  # Skip invalid values
                
    for y in years_en_cours:
        if y[0] is not None:  # Check if value exists
            try:
                year_val = int(float(y[0]))
                if year_val > 0:  # Only add positive years
                    all_years.append(year_val)
            except (ValueError, TypeError):
                continue  # Skip invalid values
            
    # Remove duplicates and sort
    years = sorted(list(set(all_years)), reverse=True)
    
    # Get unique types for filter dropdown
    types = db.session.query(
        db.distinct(DemandeVacances.type_vacances)
    ).filter(DemandeVacances.type_vacances.isnot(None)).all()
    types = [t[0] for t in types if t[0] is not None and t[0].strip()]
    
    return render_template('vacances/archive.html',
                         demandes=demandes,
                         years=years,
                         types=types,
                         current_year=year,
                         current_status=status,
                         current_type=type_vacances,
                         current_search=search) 