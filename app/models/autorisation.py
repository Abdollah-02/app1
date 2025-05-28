from datetime import datetime
from app import db

class Autorisation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    date_sortie = db.Column(db.Date, nullable=False)
    heure_sortie = db.Column(db.Time, nullable=False)
    date_retour = db.Column(db.Date, nullable=False)
    heure_retour = db.Column(db.Time, nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    motif = db.Column(db.String(500), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    statut = db.Column(db.String(20), default='En attente')  # En attente, Approuvé, Refusé
    signature_responsable = db.Column(db.Boolean, default=False)
    createur = db.Column(db.String(80))  # Username of the creator
    signature_data = db.Column(db.Text, nullable=True)  # To store signature image data

    def __repr__(self):
        return f'<Autorisation {self.nom} {self.prenom} - {self.date_sortie}>' 