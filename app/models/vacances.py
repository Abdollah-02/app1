from app import db
from datetime import datetime

class DemandeVacances(db.Model):
    __tablename__ = 'demande_vacances'
    
    id = db.Column(db.Integer, primary_key=True)
    unite = db.Column(db.String(100), nullable=False)
    type_vacances = db.Column(db.String(50), nullable=False)  # Annuel ou compensatoire
    nom_prenom = db.Column(db.String(100), nullable=False)
    emploi = db.Column(db.String(100), nullable=False)
    interet = db.Column(db.String(200))
    nombre_jours = db.Column(db.Float, nullable=False)
    
    date_sortie = db.Column(db.Date, nullable=False)
    date_entree = db.Column(db.Date, nullable=False)
    lieu_residence = db.Column(db.String(200), nullable=False)
    signature_employe = db.Column(db.Boolean, default=False)
    nom_alternatif = db.Column(db.String(100))
    
    avis_interet_direct = db.Column(db.String(500))
    avis_directeur_general = db.Column(db.String(50))
    signature_dg = db.Column(db.Boolean, default=False)
    signature_data = db.Column(db.Text)  # To store the base64 signature image
    
    # Cadre de services de gestion
    residuel = db.Column(db.Float, nullable=False, default=0)
    residuel_clarification = db.Column(db.String(200))
    annee_en_cours = db.Column(db.Float, nullable=False, default=0)
    annee_exercice = db.Column(db.Integer)
    total = db.Column(db.Float, nullable=False, default=0)
    
    # Metadata
    date_creation = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    statut = db.Column(db.String(20), nullable=False, default='En attente')  # En attente, Approuvé, Refusé
    createur = db.Column(db.String(50), nullable=False)
    
    def __repr__(self):
        return f'<DemandeVacances {self.nom_prenom} - {self.date_sortie}>' 