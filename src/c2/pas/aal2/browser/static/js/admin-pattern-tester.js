/**
 * Admin Pattern Tester for AAL2 Admin Protection Control Panel
 * Provides real-time feedback for testing URL patterns
 */

/**
 * Initialize pattern tester UI
 * @param {Object} options - Configuration options
 * @param {string} options.testButtonId - ID of test button
 * @param {string} options.testInputId - ID of test URL input field
 * @param {string} options.resultDivId - ID of result display div
 * @param {string} options.patternsFieldId - ID of patterns field (to get current patterns)
 */
function initPatternTester(options) {
  const testButton = document.getElementById(options.testButtonId);
  const testInput = document.getElementById(options.testInputId);
  const resultDiv = document.getElementById(options.resultDivId);

  if (!testButton || !testInput || !resultDiv) {
    console.error('Pattern tester: Required elements not found');
    return;
  }

  // Attach click event to test button
  testButton.addEventListener('click', function() {
    testPattern(options);
  });

  // Also test on Enter key in input field
  testInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      testPattern(options);
    }
  });

  console.log('Pattern tester initialized');
}

/**
 * Test URL against configured patterns
 * @param {Object} options - Configuration options
 */
function testPattern(options) {
  const testInput = document.getElementById(options.testInputId);
  const resultDiv = document.getElementById(options.resultDivId);

  if (!testInput || !resultDiv) {
    console.error('Pattern tester: Elements not found');
    return;
  }

  const testUrl = testInput.value.trim();

  if (!testUrl) {
    showResult(resultDiv, {
      type: 'warning',
      message: 'Please enter a URL to test'
    });
    return;
  }

  // Get current patterns from form
  const patterns = getCurrentPatterns(options.patternsFieldId);

  if (!patterns || patterns.length === 0) {
    showResult(resultDiv, {
      type: 'warning',
      message: 'No patterns configured. Add patterns above to test matching.'
    });
    return;
  }

  // Test URL against patterns using client-side glob matching
  const matchedPatterns = [];
  patterns.forEach(function(pattern) {
    if (matchGlob(testUrl, pattern)) {
      matchedPatterns.push(pattern);
    }
  });

  // Display results
  if (matchedPatterns.length > 0) {
    showResult(resultDiv, {
      type: 'success',
      message: 'URL matches ' + matchedPatterns.length + ' pattern(s)',
      patterns: matchedPatterns,
      url: testUrl
    });
  } else {
    showResult(resultDiv, {
      type: 'info',
      message: 'URL does not match any configured patterns',
      url: testUrl
    });
  }
}

/**
 * Get current patterns from form field
 * @param {string} fieldId - ID of patterns field (or base ID for z3c.form)
 * @returns {Array} Array of pattern strings
 */
function getCurrentPatterns(fieldId) {
  // Try to find the patterns field - z3c.form may add additional structure
  let patternsField = document.getElementById(fieldId);

  if (!patternsField) {
    // Try common z3c.form field naming patterns
    patternsField = document.querySelector('[id*="admin_protected_patterns"]');
  }

  if (!patternsField) {
    console.warn('Patterns field not found, trying textarea elements');
    // Fallback: look for textarea with patterns
    const textareas = document.querySelectorAll('textarea');
    for (let i = 0; i < textareas.length; i++) {
      if (textareas[i].value.includes('*/@@') || textareas[i].value.includes('*/manage')) {
        patternsField = textareas[i];
        break;
      }
    }
  }

  if (!patternsField) {
    console.error('Could not find patterns field');
    return [];
  }

  // Parse patterns from field value
  // z3c.form List widgets typically use textarea with one pattern per line
  const fieldValue = patternsField.value;
  const patterns = fieldValue
    .split('\n')
    .map(function(line) { return line.trim(); })
    .filter(function(line) { return line.length > 0; });

  return patterns;
}

/**
 * Simple glob pattern matching
 * Supports * (any chars) and ? (single char)
 * @param {string} text - Text to match against
 * @param {string} pattern - Glob pattern
 * @returns {boolean} True if text matches pattern
 */
function matchGlob(text, pattern) {
  // Escape special regex characters except * and ?
  const regexPattern = pattern
    .replace(/[.+^${}()|[\]\\]/g, '\\$&')  // Escape special chars
    .replace(/\*/g, '.*')                   // * becomes .*
    .replace(/\?/g, '.');                   // ? becomes .

  const regex = new RegExp('^' + regexPattern + '$');
  return regex.test(text);
}

/**
 * Display test results
 * @param {HTMLElement} resultDiv - Container div for results
 * @param {Object} result - Result object with type, message, optional patterns and url
 */
function showResult(resultDiv, result) {
  resultDiv.style.display = 'block';

  // Determine message class based on type
  let messageClass = 'portalMessage';
  if (result.type === 'success') {
    messageClass += ' info';
  } else if (result.type === 'warning') {
    messageClass += ' warning';
  } else if (result.type === 'error') {
    messageClass += ' error';
  } else {
    messageClass += ' info';
  }

  // Build HTML content
  let html = '<div class="' + messageClass + '">';
  html += '<strong>' + result.message + '</strong>';

  if (result.url) {
    html += '<div style="margin-top: 0.5em;"><strong>Tested URL:</strong> <code>' + escapeHtml(result.url) + '</code></div>';
  }

  if (result.patterns && result.patterns.length > 0) {
    html += '<div style="margin-top: 0.5em;"><strong>Matched Patterns:</strong><ul style="margin: 0.5em 0;">';
    result.patterns.forEach(function(pattern) {
      html += '<li><code>' + escapeHtml(pattern) + '</code></li>';
    });
    html += '</ul></div>';
  }

  html += '</div>';

  resultDiv.innerHTML = html;
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Validate pattern syntax (client-side validation)
 * @param {string} pattern - Pattern to validate
 * @returns {Object} Validation result with valid (boolean) and error (string) properties
 */
function validatePattern(pattern) {
  if (!pattern || !pattern.trim()) {
    return {
      valid: false,
      error: 'Empty pattern not allowed'
    };
  }

  // Check for overly broad patterns
  if (pattern === '*' || pattern === '**') {
    return {
      valid: false,
      error: 'Pattern is too broad (matches everything)'
    };
  }

  // Check for invalid characters
  const invalidChars = ['<', '>', '"', '\n', '\r'];
  for (let i = 0; i < invalidChars.length; i++) {
    if (pattern.indexOf(invalidChars[i]) !== -1) {
      return {
        valid: false,
        error: 'Contains invalid character: ' + invalidChars[i]
      };
    }
  }

  // Warn if no wildcards (might be too specific)
  if (pattern.indexOf('*') === -1 && pattern.indexOf('?') === -1) {
    return {
      valid: true,
      warning: 'Pattern has no wildcards - may be too specific'
    };
  }

  return {
    valid: true
  };
}

/**
 * Add real-time pattern validation to form
 * This can be called to add validation feedback as users type patterns
 * @param {string} patternsFieldId - ID of patterns field
 */
function addPatternValidation(patternsFieldId) {
  const patternsField = document.getElementById(patternsFieldId);

  if (!patternsField) {
    console.warn('Patterns field not found for validation');
    return;
  }

  // Create validation feedback div
  const feedbackDiv = document.createElement('div');
  feedbackDiv.id = 'pattern-validation-feedback';
  feedbackDiv.style.marginTop = '0.5em';
  patternsField.parentNode.insertBefore(feedbackDiv, patternsField.nextSibling);

  // Add change event listener
  patternsField.addEventListener('change', function() {
    validatePatternsField(patternsField, feedbackDiv);
  });

  // Also validate on blur
  patternsField.addEventListener('blur', function() {
    validatePatternsField(patternsField, feedbackDiv);
  });
}

/**
 * Validate all patterns in field and show feedback
 * @param {HTMLElement} patternsField - Patterns field element
 * @param {HTMLElement} feedbackDiv - Feedback display div
 */
function validatePatternsField(patternsField, feedbackDiv) {
  const patterns = patternsField.value
    .split('\n')
    .map(function(line) { return line.trim(); })
    .filter(function(line) { return line.length > 0; });

  const errors = [];
  const warnings = [];

  patterns.forEach(function(pattern, index) {
    const validation = validatePattern(pattern);
    if (!validation.valid) {
      errors.push('Pattern ' + (index + 1) + ': ' + validation.error);
    } else if (validation.warning) {
      warnings.push('Pattern ' + (index + 1) + ': ' + validation.warning);
    }
  });

  // Display feedback
  let html = '';

  if (errors.length > 0) {
    html += '<div class="portalMessage error"><strong>Errors:</strong><ul>';
    errors.forEach(function(error) {
      html += '<li>' + escapeHtml(error) + '</li>';
    });
    html += '</ul></div>';
  }

  if (warnings.length > 0) {
    html += '<div class="portalMessage warning"><strong>Warnings:</strong><ul>';
    warnings.forEach(function(warning) {
      html += '<li>' + escapeHtml(warning) + '</li>';
    });
    html += '</ul></div>';
  }

  if (errors.length === 0 && warnings.length === 0 && patterns.length > 0) {
    html = '<div class="portalMessage info">All patterns are valid ✓</div>';
  }

  feedbackDiv.innerHTML = html;
}
