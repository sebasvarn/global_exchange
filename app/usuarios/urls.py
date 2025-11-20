"""
Configuración de rutas para la aplicación de usuarios.

Define las URLs para registro, login, verificación de email, gestión de roles y sesiones.
"""

from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),

    # Autenticación
    path('login/', views.login_view, name='login'),
    path('login/verify/', views.login_verify, name='login_verify'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro, name='registro'),  # Registro público
    path('verificar/<uidb64>/<token>/', views.verificar_email, name='verificar'),

    # Recuperación de contraseña
    path('password_reset/', views.password_reset_request, name='password_reset'),
    path('password_reset_done/', views.password_reset_done, name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),

    # Gestión de usuarios
    path('usuarios/', views.usuarios_list, name='usuarios_list'),
    path('usuarios/crear/', views.usuario_create, name='usuario_create'),  # NUEVA: Crear usuario interno
    path('usuarios/<int:user_id>/editar/', views.usuario_edit, name='usuario_edit'),
    path('usuarios/<int:user_id>/eliminar/', views.usuario_delete, name='usuario_delete'),
    path('usuarios/<int:user_id>/roles/', views.ver_usuario_roles, name='ver_usuario_roles'),
    path('usuarios/<int:user_id>/asignar-rol/', views.asignar_rol_a_usuario, name='asignar_rol'),
    path('usuarios/<int:user_id>/usuario_restore/', views.usuario_restore, name='usuario_restore'),

    #Asignar Clientes a un Usuario
    path("<int:user_id>/asignar-clientes/", views.asignar_clientes_a_usuario, name="asignar_clientes"),

    # Perfil del usuario autenticado
    path('perfil/', views.perfil, name='perfil'),
    path('seguridad/', views.security_settings, name='security_settings'),

    # Gestión de roles
    path('roles/', views.roles_list, name='roles_list'),
    # path('roles/nuevo/', views.rol_create, name='rol_create'),
    path('roles/<int:role_id>/editar/', views.rol_edit, name='rol_edit'),
    path('roles/<int:role_id>/eliminar/', views.rol_delete, name='rol_delete'),
    path('roles/<int:role_id>/role_restore/', views.role_restore, name='role_restore'),
]

