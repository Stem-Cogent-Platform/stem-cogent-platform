# Application Load Balancer module

This module owns the public Phase 1 edge: an internet-facing ALB, explicit API
and frontend host routing, HTTP-to-HTTPS redirect, a DNS-validated ACM
certificate, Route 53 aliases, managed WAF protections, and private lifecycle-
managed ALB access logs.

The HTTPS listener returns 404 for unknown host headers. Only the two canonical
hostnames can reach application target groups. The port 80 listener has no
forward action and can only redirect to TLS.
