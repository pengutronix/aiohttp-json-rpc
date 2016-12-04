from django.db import models


class Item(models.Model):
    client_id = models.IntegerField()
    number = models.IntegerField()

    def __str__(self):
        return 'client_id: {}, number: {}'.format(self.client_id, self.number)
