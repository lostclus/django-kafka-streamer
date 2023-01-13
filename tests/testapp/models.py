from django.db import models


class ModelA(models.Model):
    field1 = models.IntegerField()
    field2 = models.CharField(max_length=10)


class ModelB(models.Model):
    x = models.IntegerField()
    y = models.IntegerField()


class ModelC(models.Model):
    a = models.ForeignKey(ModelA, on_delete=models.CASCADE)
    b = models.ForeignKey(ModelB, on_delete=models.CASCADE)
