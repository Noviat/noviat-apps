.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===============================================================
Customer invoices with Belgian OGM/VCS structured communication
===============================================================

The standard account module allows to define per journal the standard used to generate customer payment references.
This approach forces a company to use multiple sales journals when they require multiple standards:
e.g. OGM/VCS for Belgium, ISO 11649 for some countries, Invoice Number for other ones.

This module allows to use a single sales journal and define the payment reference standard on the customer record.
The module also generates the payment reference dynamically whereas the standard approach will do so only when
posting the invoice.

There are also more ways to generate a structured reference for the Belgian "OGM-VCS" standard aka BBA.

For each customer, you can configure an algorithm for the generation of the OGM/VCS communication :
  - Random
  - Date
  - Partner Reference (The reference of the partner must have at least 3 digits and a maximum of 7 digits)
  
A few more small usability enhancements are also activated when installing this module suh as
more intuitive terms on the configuration settings.


Usage
=====

You have two ways to configure the module and the generation of the structured reference OGM-VCS :

  1. Configure Sales Journal with the Communication Standard 'Belgian OGM-VCS Structured Communication'.

     Use this when you want to have a Belgian Structure Reference for all Sales invoices.

        .. image:: ./static/description/journal.png

  2. Configure Sales Journal with the Communication standard 'Defined on Customer record'.
     
     Now you can configure the Payment Communication Type on your Customer records.
     
     Some Customers can be set to 'OGM-VCS' while others can be 'ISO 11649' or 'Open'

        .. image:: ./static/description/customer.png


Technical
=========

On the technical side, you can add additional algorithms.
You can look into the method "_generate_bbacomm" to see how to add your own algorithm.


Known Issues / Roadmap
======================

Add Unit tests.
