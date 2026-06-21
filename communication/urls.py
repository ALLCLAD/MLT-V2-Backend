from django.urls import path
from . import views

urlpatterns = [
    # Liste des contacts autorisés par rôle
    path('contacts/', views.ContactListView.as_view(), name='contacts'),

    # Historique de discussion avec un contact (GET)
    path('messages/<int:contact_id>/', views.MessageView.as_view(), name='discussion'),

    # Envoyer un message (POST)
    path('messages/envoyer/', views.MessageView.as_view(), name='envoyer_message'),

    # Liste des notifications de l'utilisateur connecté (GET)
    path('notifications/', views.NotificationView.as_view(), name='notifications'),

    # marquer toutes les notifications comme lue
    path('notifications/tout-lire/', views.NotificationView.as_view(), name='notifications_tout_lire'),

    # NOUVELLE ROUTE : Tout supprimer
    path('notifications/tout-supprimer/', views.NotificationView.as_view(), name='notifications_tout_supprimer'),

    # Marquer une notification comme lue (PATCH)
    path('notifications/<int:notif_id>/lire/', views.NotificationLireView.as_view(), name='lire_notification'),

    # NOUVELLE ROUTE : Supprimer une notif spécifique
    path('notifications/<int:notif_id>/supprimer/', views.NotificationSupprimerView.as_view(), name='supprimer_notification'),

    # Enregistrer la lecture d'un cours (POST)
    # → déclenche notif "Cours Lu" vers Parents et Enseignants
    path('lecture/<int:lecon_id>/', views.EnregistrerLectureView.as_view(), name='enregistrer_lecture'),

    # Notification groupée de fin d'exercices de leçon (POST)
    # → UNE SEULE notif "Exercices terminés / non terminés" à la fin de TOUS les exercices
    path('fin-exercices/', views.FinExercicesView.as_view(), name='fin_exercices'),
]
