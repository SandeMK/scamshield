/// Shared UI helpers: FR-04 colour coding per classification.
library;

import 'package:flutter/material.dart';

Color classificationColor(String c) => switch (c) {
      'CRITICAL' => const Color(0xFFC62828),
      'HIGH_RISK' => const Color(0xFFE64A19),
      'MEDIUM_RISK' => const Color(0xFFF9A825),
      'LOW_RISK' => const Color(0xFF9E9D24),
      'SAFE' => const Color(0xFF2E7D32),
      'OFFLINE' => const Color(0xFF616161),
      _ => const Color(0xFF757575),
    };

String classificationLabel(String c) => c.replaceAll('_', ' ');
