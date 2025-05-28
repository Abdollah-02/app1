from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, make_response, session, jsonify
from app.models.autorisation import Autorisation
from app import db
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from app.routes.auth import login_required, role_required
import os
from flask_login import current_user
import base64, tempfile
from app import csrf
from app.models.user import User
from app.models.vacances import DemandeVacances

bp = Blueprint('main', __name__)

@bp.route('/')
@login_required
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    # Get recent authorizations
    autorisations = Autorisation.query.order_by(Autorisation.date_creation.desc()).limit(5).all()
    
    # Get recent vacation requests
    demandes_vacances = DemandeVacances.query.order_by(DemandeVacances.date_creation.desc()).limit(5).all()
    
    return render_template('index.html', 
                         autorisations=autorisations,
                         demandes_vacances=demandes_vacances)

@csrf.exempt
@bp.route('/nouvelle-autorisation', methods=['GET', 'POST'])
@login_required
@role_required('HR')
def nouvelle_autorisation():
    if request.method == 'POST':
        autorisation = Autorisation(
            nom=request.form['nom'],
            prenom=request.form['prenom'],
            date_sortie=datetime.strptime(request.form['date_sortie'], '%Y-%m-%d').date(),
            heure_sortie=datetime.strptime(request.form['heure_sortie'], '%H:%M').time(),
            date_retour=datetime.strptime(request.form['date_retour'], '%Y-%m-%d').date(),
            heure_retour=datetime.strptime(request.form['heure_retour'], '%H:%M').time(),
            destination=request.form['destination'],
            motif=request.form['motif'],
            createur=current_user.username
        )
        db.session.add(autorisation)
        db.session.commit()
        flash('Autorisation créée avec succès!', 'success')
        return redirect(url_for('main.index'))
    
    return render_template('nouvelle_autorisation.html')

@bp.route('/autorisation/<int:id>')
@login_required
def voir_autorisation(id):
    autorisation = Autorisation.query.get_or_404(id)
    return render_template('voir_autorisation.html', autorisation=autorisation, user_role=current_user.role)

@csrf.exempt
@bp.route('/autorisation/<int:id>/approuver', methods=['GET'])
@login_required
@role_required('DG')
def approuver_autorisation(id):
    autorisation = Autorisation.query.get_or_404(id)
    
    # Check if the current user is DRH
    if current_user.username == 'DRH':
        # For DRH: only set approval status without signature
        autorisation.statut = 'Approuvé'
        autorisation.signature_responsable = True
        autorisation.signature_data = None  # Ensure no signature is stored
        db.session.commit()
        flash('Autorisation approuvée!', 'success')
        return redirect(url_for('main.index'))
    
    # For DG: include signature
    signature_path = os.path.join(current_app.static_folder, 'images', 'signatures', 'manager_signature.png')
    
    if os.path.exists(signature_path):
        with open(signature_path, 'rb') as img_file:
            signature_data = base64.b64encode(img_file.read()).decode('utf-8')
            signature_data = f'data:image/png;base64,{signature_data}'
            
            autorisation.signature_data = signature_data
            autorisation.statut = 'Approuvé'
            autorisation.signature_responsable = True
            db.session.commit()
            
            flash('Autorisation approuvée avec signature!', 'success')
            return redirect(url_for('main.index'))
    
    flash('Erreur: Image de signature non trouvée', 'error')
    return redirect(url_for('main.index'))

@bp.route('/autorisation/<int:id>/refuser')
@login_required
@role_required('DG')
def refuser_autorisation(id):
    autorisation = Autorisation.query.get_or_404(id)
    autorisation.statut = 'Refusé'
    db.session.commit()
    flash('Autorisation refusée!', 'success')
    return redirect(url_for('main.index'))

@bp.route('/autorisation/<int:id>/supprimer')
@login_required
def supprimer_autorisation(id):
    if not current_user.is_authenticated or current_user.role != 'DG':
        flash('Seul le DG peut supprimer les autorisations.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        autorisation = Autorisation.query.get_or_404(id)
        db.session.delete(autorisation)
        db.session.commit()
        flash('Autorisation supprimée avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erreur lors de la suppression de l\'autorisation.', 'danger')
    
    return redirect(url_for('main.index'))

@csrf.exempt
@bp.route('/autorisation/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required('DG')
def modifier_autorisation(id):
    if not current_user.is_authenticated or current_user.role != 'DG':
        flash('Seul le DG peut modifier les autorisations.', 'danger')
        return redirect(url_for('main.index'))
        
    autorisation = Autorisation.query.get_or_404(id)
    if request.method == 'POST':
        try:
            # Get form data
            date_sortie = datetime.strptime(request.form['date_sortie'], '%Y-%m-%d')
            heure_sortie = datetime.strptime(request.form['heure_sortie'], '%H:%M')
            date_retour = datetime.strptime(request.form['date_retour'], '%Y-%m-%d')
            heure_retour = datetime.strptime(request.form['heure_retour'], '%H:%M')

            # Update autorisation
            autorisation.nom = request.form['nom']
            autorisation.prenom = request.form['prenom']
            autorisation.date_sortie = date_sortie.date()
            autorisation.heure_sortie = heure_sortie.time()
            autorisation.date_retour = date_retour.date()
            autorisation.heure_retour = heure_retour.time()
            autorisation.destination = request.form['destination']
            autorisation.motif = request.form['motif']
            
            db.session.commit()
            flash('Autorisation modifiée avec succès.', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            db.session.rollback()
            print(f"Error: {str(e)}")  # For debugging
            flash('Erreur lors de la modification de l\'autorisation.', 'danger')
            
    return render_template('modifier_autorisation.html', autorisation=autorisation)

def create_authorization_pdf(autorisation, buffer):
    # Création du PDF
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Logo
    logo_path = os.path.join(current_app.static_folder, 'images', 'gmi-logo.png')
    if os.path.exists(logo_path):
        c.drawImage(logo_path, 30*mm, 260*mm, width=40*mm, height=40*mm)

    # En-tête
    c.setFont("Helvetica-Bold", 13)
    c.drawString(80*mm, 270*mm, "EURL G.M.I ALGÉRIE")
    
    c.setFont("Helvetica", 9)
    c.drawString(80*mm, 265*mm, "FABRICATION & MONTAGE DES ÉQUIPEMENTS ÉLECTRIQUES ET HYDRAULIQUES")
    c.drawString(80*mm, 260*mm, "GROUPES ÉLECTROGÈNES, GROUPES DE SOUDAGE")
    c.drawString(80*mm, 255*mm, "ZONE INDUSTRIELLE Oued Sly W. Chlef")
    c.drawString(80*mm, 250*mm, "Tél: 020656464 / 020656666 | Fax: 020656588")

    # Titre
    c.setFont("Helvetica-Bold", 11)
    c.drawString(30*mm, 230*mm, "AUTORISATION DE SORTIE")
    c.drawString(30*mm, 225*mm, "POUR DES RAISONS PERSONNELLES")
    c.setFont("Helvetica", 8)
    c.drawString(30*mm, 220*mm, "(Exemplaire Entreprise)")

    # Informations
    c.setFont("Helvetica-Bold", 10)
    y = 200
    c.drawString(30*mm, y*mm, f"NOM : {autorisation.nom}")
    c.drawString(120*mm, y*mm, f"PRÉNOM : {autorisation.prenom}")
    
    y -= 10
    c.drawString(30*mm, y*mm, f"DATE DE SORTIE : {autorisation.date_sortie.strftime('%d/%m/%Y')}")
    c.drawString(120*mm, y*mm, f"HEURE : {autorisation.heure_sortie.strftime('%H:%M')}")
    
    y -= 10
    c.drawString(30*mm, y*mm, f"DATE DE RETOUR : {autorisation.date_retour.strftime('%d/%m/%Y')}")
    c.drawString(120*mm, y*mm, f"HEURE : {autorisation.heure_retour.strftime('%H:%M')}")
    
    y -= 10
    c.drawString(30*mm, y*mm, f"DESTINATION : {autorisation.destination}")
    
    y -= 10
    c.drawString(30*mm, y*mm, f"MOTIF DE SORTIE : {autorisation.motif}")

    # Signature première copie (Company copy)
    y -= 25
    c.setFont("Helvetica-Bold", 10)
    c.drawString(120*mm, y*mm, "RESPONSABLE HIÉRARCHIQUE /")
    if autorisation.signature_responsable:
        y -= 8
        c.setFillColor(colors.green)
        c.drawString(120*mm, y*mm, "Document approuvé")
        c.setFillColor(colors.black)
        
        # Only add signature image if it exists (DG approval)
        if autorisation.signature_data:
            image_data = autorisation.signature_data.split(',')[1]
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_file.write(base64.b64decode(image_data))
                temp_file.flush()
                
                # Draw the signature image
                c.drawImage(temp_file.name, 120*mm, (y-20)*mm, width=20*mm, height=10*mm)
                
            os.unlink(temp_file.name)
            
    elif autorisation.statut == 'Refusé':
        y -= 8
        c.setFillColor(colors.red)
        c.drawString(120*mm, y*mm, "Document refusé")
        c.setFillColor(colors.black)

    # Ligne de séparation
    y -= 20
    c.line(30*mm, y*mm, 180*mm, y*mm)

    # Deuxième copie
    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawString(30*mm, y*mm, "AUTORISATION DE SORTIE")
    y -= 5
    c.drawString(30*mm, y*mm, "POUR DES RAISONS PERSONNELLES")
    c.setFont("Helvetica", 8)
    y -= 5
    c.drawString(30*mm, y*mm, "(Exemplaire Employé)")

    # Informations deuxième copie
    c.setFont("Helvetica-Bold", 10)
    y -= 20
    c.drawString(30*mm, y*mm, f"NOM : {autorisation.nom}")
    c.drawString(120*mm, y*mm, f"PRÉNOM : {autorisation.prenom}")
    
    y -= 10
    c.drawString(30*mm, y*mm, f"DATE DE SORTIE : {autorisation.date_sortie.strftime('%d/%m/%Y')}")
    c.drawString(120*mm, y*mm, f"HEURE : {autorisation.heure_sortie.strftime('%H:%M')}")
    
    y -= 10
    c.drawString(30*mm, y*mm, f"DATE DE RETOUR : {autorisation.date_retour.strftime('%d/%m/%Y')}")
    c.drawString(120*mm, y*mm, f"HEURE : {autorisation.heure_retour.strftime('%H:%M')}")
    
    y -= 10
    c.drawString(30*mm, y*mm, f"DESTINATION : {autorisation.destination}")
    
    y -= 10
    c.drawString(30*mm, y*mm, f"MOTIF DE SORTIE : {autorisation.motif}")

    # Signature deuxième copie (Employee copy)
    y -= 15
    c.setFont("Helvetica-Bold", 10)
    c.drawString(120*mm, y*mm, "RESPONSABLE HIÉRARCHIQUE /")
    if autorisation.signature_responsable:
        y -= 6
        c.setFillColor(colors.green)
        c.drawString(120*mm, y*mm, "Document approuvé")
        c.setFillColor(colors.black)
        
        # Add signature image to employee copy as well
        if autorisation.signature_data:
            # Remove the data URL prefix to get just the base64 data
            image_data = autorisation.signature_data.split(',')[1]
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_file.write(base64.b64decode(image_data))
                temp_file.flush()
                
                # Draw the signature image
                c.drawImage(temp_file.name, 120*mm, (y-20)*mm, width=20*mm, height=10*mm)
                
            # Clean up the temporary file
            os.unlink(temp_file.name)
            
    elif autorisation.statut == 'Refusé':
        y -= 6
        c.setFillColor(colors.red)
        c.drawString(120*mm, y*mm, "Document refusé")
        c.setFillColor(colors.black)

    c.save()

@bp.route('/autorisation/<int:id>/pdf')
def telecharger_pdf(id):
    try:
        autorisation = Autorisation.query.get_or_404(id)
        
        # Créer un buffer pour le PDF
        buffer = BytesIO()
        
        # Générer le PDF
        create_authorization_pdf(autorisation, buffer)
        
        # Préparer la réponse
        buffer.seek(0)
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=autorisation_{id}.pdf'
        
        return response
    
    except Exception as e:
        flash(f'Erreur lors de la génération du PDF: {str(e)}', 'error')
        return redirect(url_for('main.voir_autorisation', id=id))

@bp.route('/autorisations')
@login_required
def liste_autorisations():
    autorisations = Autorisation.query.order_by(Autorisation.date_creation.desc()).all()
    return render_template('liste_autorisations.html', autorisations=autorisations) 