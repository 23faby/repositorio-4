import uuid

from flask import request, flash, render_template, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, validators

from app.auth.base import auth_bp
from app.auth.views.login_utils import after_login
from app.auth_utils import check_pwnedpasswords
from app.db import Session
from app.extensions import limiter
from app.models import ResetPasswordCode


class ResetPasswordForm(FlaskForm):
    password = StringField(
        "Password",
        validators=[validators.DataRequired(), validators.Length(min=8, max=100)],
    )


@auth_bp.route("/reset_password", methods=["GET", "POST"])
@limiter.limit("10/minute")
def reset_password():
    form = ResetPasswordForm(request.form)

    reset_password_code_str = request.args.get("code")

    reset_password_code: ResetPasswordCode = ResetPasswordCode.get_by(
        code=reset_password_code_str
    )

    if not reset_password_code:
        error = (
            "The reset password link can be used only once. "
            "Please request a new link to reset password."
        )
        return render_template("auth/reset_password.html", form=form, error=error)

    if reset_password_code.is_expired():
        error = "The link has been already expired. Please make a new request of the reset password link"
        return render_template("auth/reset_password.html", form=form, error=error)

    if form.validate_on_submit():
        user = reset_password_code.user
        new_password = form.password.data

        # avoid user reusing the old password
        if user.check_password(new_password):
            error = "You cannot reuse the same password"
            return render_template("auth/reset_password.html", form=form, error=error)
        if check_pwnedpasswords(new_password):
            error = "Password found in a breach, please try a different password."
            return render_template("auth/reset_password.html", form=form, error=error)

        user.set_password(new_password)

        flash("Your new password has been set", "success")

        # this can be served to activate user too
        user.activated = True

        # remove the reset password code
        ResetPasswordCode.delete(reset_password_code.id)

        # change the alternative_id to log user out on other browsers
        user.alternative_id = str(uuid.uuid4())

        Session.commit()

        # do not use login_user(user) here
        # to make sure user needs to go through MFA if enabled
        return after_login(user, url_for("dashboard.index"))

    return render_template("auth/reset_password.html", form=form)
