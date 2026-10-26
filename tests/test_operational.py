import json
import tempfile
import unittest
from pathlib import Path

from calling_crm.db import Database
from calling_crm.quotes import calculate_quote, generate_pdf, render_quote_template
from calling_crm.mailer import make_message


class OperationalTests(unittest.TestCase):
    def test_archive_restore_notes_and_history(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "crm.db"); pid = db.profiles()[0]["id"]
            cid, _ = db.upsert_contact({"company": "Fiktiva AB", "name": "Testperson", "phone": "0700"}, pid)
            db.save_notes(cid, "Ring efter lunch"); db.log_call(cid, "manual", "contacted", "Svarade")
            self.assertEqual(len(db.events_for(cid)), 2); db.archive_contact(cid)
            self.assertEqual(db.list_contacts(pid), []); db.restore_contact(cid)
            self.assertEqual(len(db.list_contacts(pid)), 1); db.close()

    def test_decimal_quote_and_pdf(self):
        quote = calculate_quote(base_price="1000", participants="3", price_per_participant="125.50", travel_km="100", km_rate="2.50", catering="50", vat_rate="25")
        self.assertEqual(quote["internal_total"], "1676.50")
        self.assertEqual(quote["vat_amount"], "419.13")
        self.assertEqual(render_quote_template("{{company_name}} {{total_price_inc_vat}}", {"company_name":"Fiktiva AB", "total_price_inc_vat":quote["total_price_inc_vat"]}), "Fiktiva AB 2095.63")
        with tempfile.TemporaryDirectory() as folder:
            pdf = generate_pdf(Path(folder) / "quote.pdf", title="Offert", lines=["Fiktiva AB", "Pris: 1 626,50 SEK"])
            self.assertTrue(pdf.read_bytes().startswith(b"%PDF-1.4"))

    def test_quote_calculation_uses_selected_addons_and_zero_override(self):
        quote=calculate_quote(base_price="1 000",participants="2",price_per_participant="750",travel_km="23,5",km_rate="30,50",catering="200",overnight="900",vat_rate="25",include=["travel_cost","catering"])
        self.assertEqual(quote["internal_total"],"3416.75")
        zero=calculate_quote(base_price="1000",participants="1",price_per_participant="500",vat_rate="25",manual_total="0")
        self.assertEqual(zero["total_price_ex_vat"],"0.00"); self.assertEqual(zero["vat_amount"],"0.00")

    def test_quote_version_is_linked_to_customer(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "crm.db"); cid, _ = db.upsert_contact({"name":"Test"}, 1)
            first, version_one = db.create_quote(cid, "Offert", {"total_price_ex_vat":"100.00"})
            second, version_two = db.create_quote(cid, "Offert", {"total_price_ex_vat":"120.00"})
            self.assertEqual((first, second), (1, 2)); self.assertEqual((version_one, version_two), (1, 2)); self.assertEqual(json.loads(db.quotes_for(cid)[0]["data_json"])["total_price_ex_vat"], "120.00"); db.close()

    def test_quote_keeps_package_snapshot_when_package_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Database(Path(folder)/"crm.db"); pid=db.profiles()[0]["id"]; product=db.create_product(pid,"Tjänst"); offer=db.create_offer(pid,product,"Paket A","Gammal beskrivning","1000 kr","25%","4","8","1 dag","Gamla villkor"); cid,_=db.upsert_contact({"company":"Fiktiva AB","name":"Anna"},pid); package=dict(db.offer(offer)); quote_id,_=db.create_quote(cid,"Paket A",{"package_snapshot":package,"total_price_ex_vat":"1000.00"},offer_id=offer); db.update_offer(offer,description="Ny beskrivning",terms="Nya villkor"); saved=json.loads(db.quotes_for(cid)[0]["data_json"]); self.assertEqual(saved["package_snapshot"]["description"],"Gammal beskrivning"); self.assertEqual(saved["package_snapshot"]["terms"],"Gamla villkor"); db.close()

    def test_offer_pdf_can_be_attached_without_marking_delivery(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf = generate_pdf(Path(folder) / "offer.pdf", title="Offert", lines=["Test"])
            message = make_message("from@example.test", "to@example.test", "Offert", "Se bilaga", attachment_path=pdf)
            self.assertEqual(message.get_filename(), None)
            self.assertIn("offer.pdf", message.as_string())


if __name__ == "__main__":
    unittest.main()
