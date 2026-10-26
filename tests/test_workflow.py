import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from calling_crm.backup import encrypt_backup, restore_backup
from calling_crm.db import Database
from calling_crm.mailer import MailError, make_message, render_template

class WorkflowTests(unittest.TestCase):
    def test_offer_validation_and_profile_scope(self):
        with tempfile.TemporaryDirectory() as d:
            db=Database(Path(d)/'crm.db'); pid=db.profiles()[0]['id']; product=db.create_product(pid,'Fiktiv tjänst')
            with self.assertRaises(ValueError): db.create_offer(pid,product,'Fel paket','', '', '', '10','2','','')
            oid=db.create_offer(pid,product,'Testpaket','Beskrivning','Pris lämnas efter överenskommelse','', '1','10','1 dag','Testvillkor')
            self.assertEqual(db.offer(oid)['price'],'Pris lämnas efter överenskommelse')
            other=db.create_profile('Annan profil'); self.assertFalse(db.offers(other))
            db.close()

    def test_editing_preserves_offer_version_and_profile_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            db=Database(Path(d)/'crm.db'); pid=db.profiles()[0]['id']; product=db.create_product(pid,'Tjänst'); oid=db.create_offer(pid,product,'Paket','','100 kr','','1','4','','Villkor')
            before=db.offer(oid)['version']; db.update_offer(oid,price='200 kr',terms='Nya villkor'); self.assertEqual(db.offer(oid)['price'],'200 kr'); self.assertEqual(db.offer(oid)['version'],before+1)
            tid=db.add_template(pid,'Mall','Ämne','Gammalt'); db.update_template(tid,body='Nytt'); self.assertEqual(db.template(tid)['body'],'Nytt')
            db.close()

    def test_followup_requires_separate_consent(self):
        with tempfile.TemporaryDirectory() as d:
            db=Database(Path(d)/'crm.db'); pid=db.profiles()[0]['id']; cid,_=db.upsert_contact({'name':'Test','email':'test@example.test'},pid)
            with self.assertRaises(PermissionError): db.add_followup_after_offer(cid)
            db.set_consent(cid,True,'followup'); self.assertEqual(db.add_followup_after_offer(cid),1)
            db.set_opt_out(cid)
            with self.assertRaises(PermissionError): db.add_followup_after_offer(cid)
            db.close()

    def test_review_render_and_consent_gates_sending(self):
        with tempfile.TemporaryDirectory() as d:
            db=Database(Path(d)/'crm.db'); pid=db.profiles()[0]['id']; product=db.create_product(pid,'Fiktiv tjänst'); oid=db.create_offer(pid,product,'Testpaket','','100 kr','25%','2','8','1 dag','Gäller i 30 dagar'); tid=db.add_template(pid,'Standard','Hej {{kontaktperson}} om {{erbjudandepaket}}','Pris {{pris}} för {{företagsnamn}}')
            cid,_=db.upsert_contact({'name':'Testperson','company':'Test AB','email':'test@example.test'},pid); self.assertFalse(db.eligible_for_information(cid))
            subject,body=render_template(db.template(tid),db.get_contact(cid),db.offer(oid),db.product(product),db.profile(pid)); self.assertIn('Testpaket',subject); self.assertIn('100 kr',body)
            with self.assertRaises(MailError): make_message('',db.get_contact(cid)['email'],subject,body)
            db.set_consent(cid,True,'information'); self.assertTrue(db.eligible_for_information(cid)); db.set_opt_out(cid); self.assertFalse(db.eligible_for_information(cid)); self.assertFalse(db.eligible_for_marketing(cid))
            db.close()

    def test_smtp_failure_is_explicit_and_no_plaintext_storage(self):
        from calling_crm.mailer import send_smtp
        msg=make_message('sender@example.test','recipient@example.test','Test','Body')
        with patch('calling_crm.mailer.smtplib.SMTP') as smtp:
            import smtplib
            smtp.return_value.__enter__.return_value.login.side_effect=smtplib.SMTPAuthenticationError(535,'rejected')
            with self.assertRaises(MailError): send_smtp(msg,'smtp.example.test',587,'user','secret')

    def test_encrypted_backup_roundtrip_and_wrong_password(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source=root/'crm.db'; backup=root/'crm.enc'; restored=root/'restored.db'; source.write_bytes(b'local sqlite test data')
            encrypt_backup(source,backup,'correct horse'); self.assertNotEqual(source.read_bytes(),backup.read_bytes())
            with self.assertRaises(Exception): restore_backup(backup,restored,'wrong password')
            restore_backup(backup,restored,'correct horse'); self.assertEqual(source.read_bytes(),restored.read_bytes())

if __name__=='__main__': unittest.main()
