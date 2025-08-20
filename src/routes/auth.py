from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from src.models.user import db, User
from src.forms import LoginForm, CreateUserForm, ChangePasswordForm, ForgotPasswordForm, ResetPasswordForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('meetings.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('meetings.dashboard')
            return redirect(next_page)
        flash('Usuário ou senha inválidos.', 'error')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
    if not current_user.is_admin:
        flash('Acesso negado. Apenas administradores podem criar usuários.', 'error')
        return redirect(url_for('meetings.dashboard'))
    
    form = CreateUserForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            is_admin=form.is_admin.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'Usuário {user.username} criado com sucesso!', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('auth/create_user.html', form=form)

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('meetings.dashboard'))
        else:
            flash('Senha atual incorreta.', 'error')
    
    return render_template('auth/change_password.html', form=form)

@auth_bp.route('/api/current_user')
@login_required
def current_user_api():
    return jsonify(current_user.to_dict())



@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('meetings.dashboard'))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            from src.utils.email_utils import send_password_reset_email
            token = user.get_reset_token()
            send_password_reset_email(user, token)
            flash('Um e-mail com instruções para redefinir sua senha foi enviado.', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('E-mail não encontrado.', 'error')
    return render_template('auth/forgot_password.html', form=form)

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('meetings.dashboard'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('Token de redefinição de senha inválido ou expirado.', 'error')
        return redirect(url_for('auth.forgot_password'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.new_password.data)
        db.session.commit()
        flash('Sua senha foi redefinida com sucesso!', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


