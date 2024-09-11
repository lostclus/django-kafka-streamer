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


class ModelD(models.Model):
    field1 = models.IntegerField()


class ModelE(models.Model):
    d = models.ForeignKey(ModelD, on_delete=models.CASCADE, related_name="e_set")


class ModelF(models.Model):
    d = models.OneToOneField(ModelD, on_delete=models.CASCADE, related_name="f")


class ModelG(models.Model):
    d_set = models.ManyToManyField(ModelD, related_name="g_set")
