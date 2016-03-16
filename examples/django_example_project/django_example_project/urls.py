from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = staticfiles_urlpatterns() + [
    url(r'', include(admin.site.urls)),
]
