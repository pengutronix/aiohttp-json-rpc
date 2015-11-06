from django.contrib import admin
from django.conf.urls import include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = staticfiles_urlpatterns() + [
    url(r'', include(admin.site.urls)),
]
