from flask import Blueprint, render_template, request, jsonify
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils import get_config, set_config
from CTFd.utils.user import get_current_user, get_current_team
from CTFd.models import db, Challenges, Submissions, Teams, Awards, Users
from CTFd.plugins import register_plugin_assets_directory, register_plugin_script
from datetime import datetime
import math 
from sqlalchemy.exc import IntegrityError

# === Modèles de base de données ===

class UnblockLog(db.Model):
    __tablename__ = "attempts_unblock_logs"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    team = db.relationship("Teams", backref="unblock_logs")
    challenge = db.relationship("Challenges", backref="unblock_logs")
    admin = db.relationship("Users", backref="unblock_logs")


class UnblockRequest(db.Model):
    __tablename__ = "attempts_remover_requests"
    __table_args__ = (
        db.UniqueConstraint('team_id', 'challenge_id', name='unique_team_challenge_request'),
    )

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    team = db.relationship("Teams", backref="attempts_remover_requests")
    challenge = db.relationship("Challenges", backref="attempts_remover_requests")


class ExcludedChallenge(db.Model):
    __tablename__ = "attempts_remover_excluded_challenges"

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False, unique=True)
    excluded_at = db.Column(db.DateTime, default=datetime.utcnow)
    excluded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    challenge = db.relationship("Challenges", backref="exclusion_logs")
    admin = db.relationship("Users", backref="exclusion_logs")


class SingleAttemptRequest(db.Model):
    __tablename__ = "attempts_remover_single_requests"
    __table_args__ = (
        db.UniqueConstraint('team_id', 'challenge_id', name='unique_team_challenge_single_request'),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    team = db.relationship("Teams", backref="single_attempt_requests")
    challenge = db.relationship("Challenges", backref="single_attempt_requests")

class SingleAttemptLog(db.Model):
    __tablename__ = "attempts_single_attempt_logs"
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    team = db.relationship("Teams", backref="single_attempt_logs")
    challenge = db.relationship("Challenges", backref="single_attempt_logs")
    admin = db.relationship("Users", backref="single_attempt_logs")


# === Plugin loader ===

def load(app):
    remover_bp = Blueprint(
        'attempts_remover',
        __name__,
        template_folder='templates',
        static_folder='assets',
        url_prefix='/plugins/ctfd-attempts-remover'
    )

    api_bp = Blueprint(
        'attempts_remover_api',
        __name__,
        url_prefix='/api/v1/attempts_remover'
    )

    # === API : Récupère les demandes en attente pour l'équipe connectée ===
    @api_bp.route("/my_requests", methods=["GET"])
    @authed_only
    def get_my_requests():
        team = get_current_team()
        requests = UnblockRequest.query.filter_by(team_id=team.id).all()
        return jsonify([{
            "challenge_id": r.challenge_id,
            "challenge_name": r.challenge.name,
            "challenge_value": r.challenge.value,
            "timestamp": r.timestamp.isoformat()
        } for r in requests])

    # === API : Récupère l'historique des déblocages acceptés pour l'équipe ===
    @api_bp.route('/my_history', methods=["GET"])
    @authed_only
    def get_my_unblock_history():
        team = get_current_team()
        if not team:
            return jsonify([])
        
        # Récupérer les deux types de logs
        full_logs = UnblockLog.query.filter_by(team_id=team.id).all()
        single_logs = SingleAttemptLog.query.filter_by(team_id=team.id).all()
        
        result = []
        
        # Logs de déblocages complets
        for l in full_logs:
            award = Awards.query.filter_by(
                team_id=team.id,
                name=f"Déblocage challenge - {l.challenge.name}"
            ).order_by(Awards.date.desc()).first()
            
            cost = abs(award.value) if award else 0
            
            result.append({
                "challenge_name": l.challenge.name,
                "timestamp": l.timestamp.isoformat(),
                "cost": cost,
                "admin_name": l.admin.name,
                "type": "full"
            })
        
        # Logs de tentatives uniques
        for l in single_logs:
            award = Awards.query.filter_by(
                team_id=team.id,
                name=f"Tentative supplémentaire - {l.challenge.name}"
            ).order_by(Awards.date.desc()).first()
            
            cost = abs(award.value) if award else 0
            
            result.append({
                "challenge_name": l.challenge.name,
                "timestamp": l.timestamp.isoformat(),
                "cost": cost,
                "admin_name": l.admin.name,
                "type": "single"
            })
        
        # Trier par date décroissante
        result.sort(key=lambda x: x["timestamp"], reverse=True)
        return jsonify(result)

    # === API : Mes demandes de tentatives uniques ===
    @api_bp.route("/my_single_requests", methods=["GET"])
    @authed_only
    def get_my_single_requests():
        team = get_current_team()
        if not team:
            return jsonify([])
        
        requests = SingleAttemptRequest.query.filter_by(team_id=team.id).all()
        return jsonify([{
            "challenge_id": r.challenge_id,
            "challenge_name": r.challenge.name,
            "challenge_value": r.challenge.value,
            "timestamp": r.timestamp.isoformat()
        } for r in requests])
        
    # === API : Créer une nouvelle demande de déblocage pour un challenge ===
    @api_bp.route('/request_support', methods=["POST"])
    @authed_only
    def request_support():
        data = request.get_json()
        challenge_id = data.get("challenge_id")
        team = get_current_team()

        if not team or not challenge_id:
            return jsonify(success=False, error="Équipe ou challenge manquant"), 400

        challenge = Challenges.query.filter_by(id=challenge_id).first()
        if not challenge:
            return jsonify(success=False, error="Challenge introuvable"), 404

        # Vérifier qu'il n'y a pas déjà une demande (déblocage complet OU tentative unique)
        existing_full = UnblockRequest.query.filter_by(team_id=team.id, challenge_id=challenge.id).first()
        existing_single = SingleAttemptRequest.query.filter_by(team_id=team.id, challenge_id=challenge.id).first()

        if existing_full:
            return jsonify(success=False, error="Une demande de déblocage complet a déjà été envoyée."), 400
        if existing_single:
            return jsonify(success=False, error="Une demande de tentative unique a déjà été envoyée."), 400

        req = UnblockRequest(team_id=team.id, challenge_id=challenge.id)
        db.session.add(req)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify(success=False, error="Une demande existe déjà"), 400
            
        return jsonify(success=True)

    # === API : Retourne les challenges actuellement bloqués ===
    @api_bp.route('/blocked', methods=["GET"])
    @authed_only
    def user_blocked_challenges():
        team = get_current_team()
        user = get_current_user()
        if not team and not user:
            return jsonify([])

        is_team_mode = team is not None
        id_used = team.id if is_team_mode else user.id
        
        # Récupérer les IDs des challenges exclus
        excluded_ids = [e.challenge_id for e in ExcludedChallenge.query.all()]
        
        challenges = Challenges.query.filter(
            Challenges.max_attempts > 0,
            ~Challenges.id.in_(excluded_ids)  # Exclure les challenges non-déblocables
        ).all()

        blocked = []
        for chal in challenges:
            # Vérifier d'abord si le challenge est déjà résolu
            solved_query = Submissions.query.filter_by(challenge_id=chal.id, type="correct")
            solved_query = solved_query.filter_by(team_id=id_used) if is_team_mode else solved_query.filter_by(user_id=id_used)
            is_solved = solved_query.first() is not None
            
            # Si déjà résolu, on ignore
            if is_solved:
                continue
            
            # Compter les tentatives incorrectes
            query = Submissions.query.filter_by(challenge_id=chal.id, type="incorrect")
            query = query.filter_by(team_id=id_used) if is_team_mode else query.filter_by(user_id=id_used)
            count = query.count()
            
            # Seulement si bloqué ET pas résolu
            if count >= chal.max_attempts:
                blocked.append({
                    "challenge_id": chal.id,
                    "challenge_name": chal.name,
                    "value": chal.value,
                    "fail_count": count,
                    "max_attempts": chal.max_attempts
                })
        return jsonify(blocked)

    # === API : Retourne la configuration actuelle du malus ===
    @api_bp.route('/config', methods=["GET"])
    @authed_only
    def get_config_route():
        return jsonify({
            "mode": get_config("attempts_remover:mode") or "fixed",
            "fixed_cost": int(get_config("attempts_remover:fixed_cost") or 100),
            "percent_cost": int(get_config("attempts_remover:percent_cost") or 10),

            "single_attempt_enabled": bool(get_config("attempts_remover:single_attempt_enabled") or False),
            "single_attempt_mode": get_config("attempts_remover:single_attempt_mode") or "fixed",
            "single_attempt_fixed_cost": int(get_config("attempts_remover:single_attempt_fixed_cost") or 50),
            "single_attempt_percent_cost": int(get_config("attempts_remover:single_attempt_percent_cost") or 5),

            "highlight_blocked_challenges": bool(get_config("attempts_remover:highlight_blocked_challenges") or False)

        })

    # === API : Permet à un admin de modifier la configuration ===
    @api_bp.route('/config', methods=["POST"])
    @admins_only
    def set_config_route():
        data = request.get_json()
        set_config("attempts_remover:mode", data.get("mode"))
        set_config("attempts_remover:fixed_cost", data.get("fixed_cost"))
        set_config("attempts_remover:percent_cost", data.get("percent_cost"))

        # Nouvelles configs pour tentative unique
        set_config("attempts_remover:single_attempt_enabled", data.get("single_attempt_enabled", False))
        set_config("attempts_remover:single_attempt_mode", data.get("single_attempt_mode", "fixed"))
        set_config("attempts_remover:single_attempt_fixed_cost", data.get("single_attempt_fixed_cost", 50))
        set_config("attempts_remover:single_attempt_percent_cost", data.get("single_attempt_percent_cost", 5))

        #Nouvelle route pour customisation bouton CTFd 
        set_config("attempts_remover:highlight_blocked_challenges", data.get("highlight_blocked_challenges", False))
        
        return jsonify(success=True)

    # === API : Retourne les logs de déblocage (admin) ===
    @api_bp.route('/unblock_logs', methods=["GET"])
    @admins_only
    def get_unblock_logs():
        # Récupérer les deux types de logs
        full_logs = UnblockLog.query.all()
        single_logs = SingleAttemptLog.query.all()
        
        # Combiner et formater
        all_logs = []
        
        for l in full_logs:
            all_logs.append({
                "timestamp": l.timestamp.isoformat(),
                "admin_name": l.admin.name,
                "team_name": l.team.name,
                "challenge_name": l.challenge.name,
                "type": "full",
                "cost": 0  # On récupérera le coût côté frontend
            })
        
        for l in single_logs:
            # Trouver l'award correspondant
            award = Awards.query.filter_by(
                team_id=l.team_id,
                name=f"Tentative supplémentaire - {l.challenge.name}"
            ).order_by(Awards.date.desc()).first()
            
            cost = abs(award.value) if award else 0
            
            all_logs.append({
                "timestamp": l.timestamp.isoformat(),
                "admin_name": l.admin.name,
                "team_name": l.team.name,
                "challenge_name": l.challenge.name,
                "type": "single",
                "cost": cost
            })
        
        # Trier par date décroissante et limiter à 50
        all_logs.sort(key=lambda x: x["timestamp"], reverse=True)
        return jsonify(all_logs[:50])

    # === API : Liste des blocages actuels toutes équipes confondues (admin) ===
    @api_bp.route('/admin_blocked', methods=["GET"])
    @admins_only
    def get_all_blocked_teams():
        challenges = Challenges.query.filter(Challenges.max_attempts > 0).all()
        teams = Teams.query.all()
        all_blocks = []
        for team in teams:
            for chal in challenges:
                fail_count = Submissions.query.filter_by(
                    team_id=team.id,
                    challenge_id=chal.id,
                    type='incorrect'
                ).count()
                if fail_count >= chal.max_attempts:
                    already_requested = UnblockRequest.query.filter_by(
                        team_id=team.id,
                        challenge_id=chal.id
                    ).first()
                    
                    # Vérifier les demandes de tentatives uniques
                    single_attempt_requested = SingleAttemptRequest.query.filter_by(
                        team_id=team.id,
                        challenge_id=chal.id
                    ).first()
                    
                    # Vérifier si le challenge est exclu
                    is_excluded = ExcludedChallenge.query.filter_by(challenge_id=chal.id).first()
                    
                    # Calculer la date du premier échec pour ce challenge
                    first_fail = Submissions.query.filter_by(
                        team_id=team.id,
                        challenge_id=chal.id,
                        type='incorrect'
                    ).order_by(Submissions.date.asc()).first()
                    
                    all_blocks.append({
                        "team_id": team.id,
                        "team_name": team.name,
                        "challenge_id": chal.id,
                        "challenge_name": chal.name,
                        "fail_count": fail_count,
                        "max_attempts": chal.max_attempts,
                        "challenge_value": chal.value,
                        "value": chal.value,
                        "requested": bool(already_requested),
                        "single_attempt_requested": bool(single_attempt_requested),  # Nouveau champ
                        "is_excluded": bool(is_excluded),
                        "blocked_date": first_fail.date.isoformat() if first_fail else None
                    })
        return jsonify(all_blocks)

    # === API : Action d’un admin pour débloquer une équipe sur un challenge ===
    @api_bp.route('/admin_unblock', methods=["POST"])
    @admins_only
    def force_unblock_team():
        data = request.get_json()
        team_id = data.get("team_id")
        challenge_id = data.get("challenge_id")

        if not team_id or not challenge_id:
            return jsonify(success=False, error="Paramètres manquants"), 400

        team = Teams.query.filter_by(id=team_id).first()
        challenge = Challenges.query.filter_by(id=challenge_id).first()

        # Vérifier si le challenge est déjà résolu
        already_solved = Submissions.query.filter_by(
            team_id=team.id,
            challenge_id=challenge.id,
            type="correct"
        ).first()

        if already_solved:
            return jsonify(success=False, error="Ce challenge est déjà résolu par cette équipe"), 400

        fails = Submissions.query.filter_by(
            challenge_id=challenge.id,
            team_id=team.id,
            type="incorrect"
        ).all()

        if not fails:
            return jsonify(success=False, error="Aucune tentative incorrecte à supprimer"), 400

        for f in fails:
            db.session.delete(f)

        mode = get_config("attempts_remover:mode") or "fixed"
        fixed_cost = int(get_config("attempts_remover:fixed_cost") or 100)
        percent_cost = int(get_config("attempts_remover:percent_cost") or 10)

        if mode == "fixed":
            cost = fixed_cost
        else:
            cost = max(1, math.ceil(abs(challenge.value) * percent_cost / 100))

        user = Users.query.filter_by(team_id=team.id).first()
        if not user:
            return jsonify(success=False, error="Aucun membre trouvé pour cette équipe"), 400

        award = Awards(
            team_id=team.id,
            user_id=user.id,
            name=f"Déblocage challenge - {challenge.name}",
            value=-cost,
            category="Malus",
            icon="shield"
        )
        db.session.add(award)

        admin = get_current_user()
        if admin:
            log = UnblockLog(
                team_id=team.id,
                challenge_id=challenge.id,
                admin_id=admin.id,
                timestamp=datetime.utcnow()
            )
            db.session.add(log)

        existing_request = UnblockRequest.query.filter_by(
            team_id=team.id,
            challenge_id=challenge.id
        ).first()
        if existing_request:
            db.session.delete(existing_request)

        db.session.commit()

        return jsonify(success=True, removed=len(fails), cost=cost, challenge=challenge.name)

    # === API : Récupérer les challenges exclus ===
    @api_bp.route('/excluded_challenges', methods=["GET"])
    @admins_only
    def get_excluded_challenges():
        excluded = ExcludedChallenge.query.all()
        return jsonify([{
            "id": e.id,
            "challenge_id": e.challenge_id,
            "challenge_name": e.challenge.name,
            "challenge_value": e.challenge.value,
            "excluded_at": e.excluded_at.isoformat(),
            "excluded_by": e.admin.name
        } for e in excluded])

    # === API : Ajouter un challenge à la liste d'exclusion ===
    @api_bp.route('/exclude_challenge', methods=["POST"])
    @admins_only
    def exclude_challenge():
        data = request.get_json()
        challenge_id = data.get("challenge_id")
        
        if not challenge_id:
            return jsonify(success=False, error="Challenge ID manquant"), 400
        
        challenge = Challenges.query.filter_by(id=challenge_id).first()
        if not challenge:
            return jsonify(success=False, error="Challenge introuvable"), 404
        
        existing = ExcludedChallenge.query.filter_by(challenge_id=challenge_id).first()
        if existing:
            return jsonify(success=False, error="Challenge déjà exclu"), 400
        
        admin = get_current_user()
        exclusion = ExcludedChallenge(
            challenge_id=challenge_id,
            excluded_by=admin.id
        )
        
        db.session.add(exclusion)
        db.session.commit()
        
        return jsonify(success=True, message=f"Challenge '{challenge.name}' exclu avec succès")

    # === API : Retirer un challenge de la liste d'exclusion ===
    @api_bp.route('/include_challenge', methods=["POST"])
    @admins_only
    def include_challenge():
        data = request.get_json()
        challenge_id = data.get("challenge_id")
        
        exclusion = ExcludedChallenge.query.filter_by(challenge_id=challenge_id).first()
        if not exclusion:
            return jsonify(success=False, error="Challenge non exclu"), 404
        
        db.session.delete(exclusion)
        db.session.commit()
        
        return jsonify(success=True, message="Challenge réintégré avec succès")

    # === API : Récupérer tous les challenges disponibles ===
    @api_bp.route('/all_challenges', methods=["GET"])
    @admins_only
    def get_all_challenges():
        challenges = Challenges.query.all()
        excluded_ids = [e.challenge_id for e in ExcludedChallenge.query.all()]
        
        return jsonify([{
            "id": c.id,
            "name": c.name,
            "value": c.value,
            "category": c.category,
            "max_attempts": c.max_attempts,
            "excluded": c.id in excluded_ids
        } for c in challenges])


    # === API : Demander une tentative supplémentaire ===
    @api_bp.route('/request_single_attempt', methods=["POST"])
    @authed_only
    def request_single_attempt():
        data = request.get_json()
        challenge_id = data.get("challenge_id")
        team = get_current_team()

        if not team or not challenge_id:
            return jsonify(success=False, error="Équipe ou challenge manquant"), 400

        # Vérifier si la fonctionnalité est activée
        if not bool(get_config("attempts_remover:single_attempt_enabled")):
            return jsonify(success=False, error="Fonctionnalité désactivée"), 400

        challenge = Challenges.query.filter_by(id=challenge_id).first()
        if not challenge:
            return jsonify(success=False, error="Challenge introuvable"), 404

        # Vérifier qu'il n'y a pas déjà une demande (déblocage complet OU tentative unique)
        existing_full = UnblockRequest.query.filter_by(team_id=team.id, challenge_id=challenge.id).first()
        existing_single = SingleAttemptRequest.query.filter_by(team_id=team.id, challenge_id=challenge.id).first()

        if existing_full:
            return jsonify(success=False, error="Une demande de déblocage complet a déjà été envoyée."), 400
        if existing_single:
            return jsonify(success=False, error="Une demande de tentative unique a déjà été envoyée."), 400

        req = SingleAttemptRequest(team_id=team.id, challenge_id=challenge.id)
        db.session.add(req)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify(success=False, error="Une demande existe déjà"), 400
            
        return jsonify(success=True)

    # === API : Mes demandes de tentatives uniques ===
    @api_bp.route('/admin_grant_single_attempt', methods=["POST"])
    @admins_only
    def grant_single_attempt():
        data = request.get_json()
        team_id = data.get("team_id")
        challenge_id = data.get("challenge_id")

        # verif les paramètres
        if not team_id or not challenge_id:
            return jsonify(success=False, error="Paramètres manquants"), 400

        # PUIS récupére les objets
        team = Teams.query.filter_by(id=team_id).first()
        challenge = Challenges.query.filter_by(id=challenge_id).first()

        if not team or not challenge:
            return jsonify(success=False, error="Équipe ou challenge introuvable"), 404

        # Vérifie si le challenge est déjà résolu
        already_solved = Submissions.query.filter_by(
            team_id=team.id,
            challenge_id=challenge.id,
            type="correct"
        ).first()

        if already_solved:
            return jsonify(success=False, error="Ce challenge est déjà résolu par cette équipe"), 400

        # Retirer seulement UNE tentative échouée (la plus récente)
        last_fail = Submissions.query.filter_by(
            challenge_id=challenge.id,
            team_id=team.id,
            type="incorrect"
        ).order_by(Submissions.date.desc()).first()

        if not last_fail:
            return jsonify(success=False, error="Aucune tentative incorrecte à retirer"), 400

        # Supprimer la tentative la plus récente
        db.session.delete(last_fail)

        # Calculer le coût
        single_mode = get_config("attempts_remover:single_attempt_mode") or "fixed"
        single_fixed_cost = int(get_config("attempts_remover:single_attempt_fixed_cost") or 50)
        single_percent_cost = int(get_config("attempts_remover:single_attempt_percent_cost") or 5)

        if single_mode == "fixed":
            cost = single_fixed_cost
        else:
            cost = max(1, math.ceil(abs(challenge.value) * single_percent_cost / 100))

        # Appliquer le malus
        user = Users.query.filter_by(team_id=team.id).first()
        if not user:
            return jsonify(success=False, error="Aucun membre trouvé pour cette équipe"), 400

        award = Awards(
            team_id=team.id,
            user_id=user.id,
            name=f"Tentative supplémentaire - {challenge.name}",
            value=-cost,
            category="Malus",
            icon="plus"
        )
        db.session.add(award)

        # Supprimer la demande
        existing_request = SingleAttemptRequest.query.filter_by(
            team_id=team.id,
            challenge_id=challenge.id
        ).first()
        if existing_request:
            db.session.delete(existing_request)

        # Créer un log de l'action
        admin = get_current_user()
        if admin:
            log = SingleAttemptLog(
                team_id=team.id,
                challenge_id=challenge.id,
                admin_id=admin.id
            )
            db.session.add(log)

        db.session.commit()

        return jsonify(success=True, cost=cost, challenge=challenge.name)

    # === Pages HTML ===

    @remover_bp.route('/unblock')
    @authed_only
    def unblock_page():
        return render_template('ctfd_attempts_remover_unblock.html')

    @remover_bp.route('/admin')
    @admins_only
    def admin_page():
        return render_template('ctfd_attempts_remover_admin.html')

    # === Initialisation plugin et BDD ===

    with app.app_context():
        #db.engine.execute("DROP TABLE IF EXISTS attempts_remover_requests")
        #db.engine.execute("DROP TABLE IF EXISTS attempts_unblock_logs")
        #db.engine.execute("DROP TABLE IF EXISTS attempts_remover_single_requests")  
        #db.engine.execute("DROP TABLE IF EXISTS attempts_single_attempt_logs")      
        #db.engine.execute("DROP TABLE IF EXISTS attempts_remover_excluded_challenges") 
        db.session.commit()
        db.create_all()

    app.register_blueprint(remover_bp)
    app.register_blueprint(api_bp)
    register_plugin_assets_directory(app, base_path='/plugins/ctfd-attempts-remover/assets')
    register_plugin_script('/plugins/ctfd-attempts-remover/assets/settingsremover.js')
