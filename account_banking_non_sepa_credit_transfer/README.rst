.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

================================================================
Non SEPA Credit Transfer - Clearing System Member Identification
================================================================

This module extends the OCA account_banking_sepa_credit_transfer module to support also non SEPA payments.

Certain banks require that payment orders contain the Clearing System Member Identifications in the outgoing payment orders.

This module adds the following fields:

- Country : Clearing System Identification
- Bank : Clearing System Member Identification (also called 'sort code' in certain countries, e.g. UK)

The following node will be added to payment order when the Clearing System Member Identification is specified on the partner's bank:

.. code-block:: XML

  <CdtrAgt>
    <FinInstnId>
      <BIC>BANKGB22</BIC>
      <ClrSysMmbId>
        <ClrSysId>
          <Cd>GBDSC</Cd>
        </ClrSysId>
        <MmbId>123456</MmbId>
      </ClrSysMmbId>
    </FinInstnId>
  </CdtrAgt>


Roadmap
=======

Add more logic to select the correct Clearing System codes based upon the exact nature of the transaction (e.g. domestic versus international payments)
