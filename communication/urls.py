from django.urls import path
from . import views

urlpatterns = [
    path('contacts/', views.ContactListView.as_view(), name='contacts'),

    # Endpoints historiques (GET)
    path('messages/private/<int:contact_id>/', views.PrivateMessageView.as_view(), name='discussion_privee'),
    path('messages/classe/<int:enseignant_id>/', views.ClasseMessageView.as_view(), name='discussion_classe'),
    path('messages/famille/<int:parent_id>/', views.FamilleMessageView.as_view(), name='discussion_famille'),

    # NOUVEAU : Point d'accès unique pour modifier ou supprimer un message
    path('messages/<int:message_id>/', views.MessageDetailView.as_view(), name='message_detail'),

    # Notifications & Métier
    path('notifications/', views.NotificationView.as_view(), name='notifications'),
    path('notifications/tout-lire/', views.NotificationView.as_view(), name='notifications_tout_lire'),
    path('notifications/tout-supprimer/', views.NotificationView.as_view(), name='notifications_tout_supprimer'),
    path('notifications/<int:notif_id>/lire/', views.NotificationLireView.as_view(), name='lire_notification'),
    path('notifications/<int:notif_id>/supprimer/', views.NotificationSupprimerView.as_view(), name='supprimer_notification'),
    path('lecture/<int:lecon_id>/', views.EnregistrerLectureView.as_view(), name='enregistrer_lecture'),
    path('fin-exercices/', views.FinExercicesView.as_view(), name='fin_exercices'),
]