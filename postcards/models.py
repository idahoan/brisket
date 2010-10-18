from django.db import models
from django.contrib.localflavor.us.models import USStateField
from simplepay.models import Transaction

BATCH_STATUS_CHOICES = (
    ('not_processed', 'Not processed'),
    ('processing', 'Processing'),
    ('processed', 'Processed'),
    ('at_printer', 'At printer'),
    ('printed', 'Printed'),
    ('mailed', 'Mailed'),
)
class Batch(models.Model):
    name = models.CharField(max_length=128)
    status = models.CharField(max_length=24, choices=BATCH_STATUS_CHOICES, default='not_processed')

POSTCARD_STATUS_CHOICES = (
    ('not_paid', 'Not paid'),
    ('paid', 'Paid'),
    ('payment_failed', 'Payment failed'),
    ('sent', 'Postcart sent'),
    ('send_failed', 'Send failed')
)
class Postcard(models.Model):
    td_id = models.CharField(max_length=32, verbose_name="Candidate")
    num_candidates = models.PositiveIntegerField(verbose_name="Number of Candidates")
    
    sender_name = models.CharField(max_length=128, verbose_name="Sender Name")
    sender_address1 = models.CharField(max_length=128, verbose_name="Sender Address Line 1")
    sender_address2 = models.CharField(max_length=128, verbose_name="Sender Address Line 2", blank=True)
    sender_state = USStateField(verbose_name="Sender State")
    sender_zip = models.CharField(max_length=10, verbose_name="Sender Zip")
    
    recipient_name = models.CharField(max_length=128, verbose_name="Recipient Name")
    recipient_address1 = models.CharField(max_length=128, verbose_name="Recipient Address Line 1")
    recipient_address2 = models.CharField(max_length=128, verbose_name="Recipient Address Line 2", blank=True)
    recipient_state = USStateField(verbose_name="Recipient State")
    recipient_zip = models.CharField(max_length=10, verbose_name="Recipient Zip")
    
    message = models.TextField()
    
    status = models.CharField(max_length=24, choices=POSTCARD_STATUS_CHOICES, default='not_paid')
    
    amazon_transaction = models.ForeignKey(Transaction, null=True, blank=True)
    pm_id = models.CharField(max_length=24, verbose_name="PostalMethods ID", blank=True)
    
    batch = models.ForeignKey(Batch, null=True, blank=True)