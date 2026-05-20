/**
 * Bug Condition Exploration Test for Deep Analysis UI Fixes
 * 
 * **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
 * 
 * **Property 1: Bug Condition** - Deep Analysis UI Bugs (GitHub Percentages, LeetCode Styling, Missing Icons)
 * 
 * **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bugs exist
 * **DO NOT attempt to fix the test or the code when it fails**
 * **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
 * **GOAL**: Surface counterexamples that demonstrate the bugs exist
 * 
 * This test uses a scoped PBT approach to test concrete failing cases for each of the 4 bugs:
 * 1. GitHub language percentages calculated incorrectly
 * 2. LeetCode contest note uses wrong CSS class
 * 3. LeetCode profile link missing icon (verify if bug exists)
 * 4. LinkedIn profile link missing icon (verify if bug exists)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GitHubAnalytics, LeetCodeAnalytics, LinkedInAnalytics } from './AnalyticsComponents';

describe('Bug Condition Exploration - Deep Analysis UI Fixes', () => {
  
  /**
   * Bug 1: GitHub language percentages calculated with (value / total_repos) * 100
   * instead of (value / total_bytes) * 100
   * 
   * Expected to FAIL on unfixed code: percentages will be wildly incorrect
   * Counterexample: JavaScript shows (50000/5)*100 = 1000000% instead of 50%
   */
  it('Bug 1: GitHub language percentages should sum to 100%', () => {
    // Sample data with known byte counts
    const githubData = {
      username: 'testuser',
      languages: {
        JavaScript: 50000,  // 50% of total
        Python: 30000,      // 30% of total
        TypeScript: 20000   // 20% of total
      },
      total_repos: 5,  // This is the wrong denominator being used
      public_repos: 5,
      total_stars: 100,
      total_forks: 50,
      followers: 20,
      following: 30,
      total_size_mb: 100,
      repo_types: { original: 3, forked: 2 },
      top_repos: []
    };

    const { container } = render(<GitHubAnalytics data={githubData} />);
    
    // Find all percentage displays in the legend (both old and new class names)
    const legendItems = container.querySelectorAll('.ana-legend-value, .ac-legend-value, .ac-legend-val');
    
    // Extract percentage values and sum them
    let totalPercentage = 0;
    const percentages = [];
    
    legendItems.forEach(item => {
      const text = item.textContent;
      // Match patterns like "50%" or "40 (40%)" or "50.0%"
      const match = text.match(/(\d+\.?\d*)\s*%/);
      if (match) {
        const pct = parseFloat(match[1]);
        percentages.push(pct);
        totalPercentage += pct;
      }
    });

    // Document the counterexample
    console.log('Bug 1 Counterexample:');
    console.log('  Languages:', Object.keys(githubData.languages));
    console.log('  Byte counts:', Object.values(githubData.languages));
    console.log('  Total repos (wrong denominator):', githubData.total_repos);
    console.log('  Total bytes (correct denominator):', 100000);
    console.log('  Displayed percentages:', percentages);
    console.log('  Sum of percentages:', totalPercentage);
    console.log('  Expected sum: 100');
    
    // Calculate what the percentages SHOULD be with wrong formula
    const wrongPercentages = Object.values(githubData.languages).map(
      bytes => (bytes / githubData.total_repos) * 100
    );
    console.log('  Wrong formula would give:', wrongPercentages, '(sum:', wrongPercentages.reduce((a,b) => a+b, 0), ')');
    
    // This assertion will FAIL on unfixed code because percentages are calculated
    // using total_repos instead of total_bytes
    // On unfixed code: JavaScript = (50000/5)*100 = 1000000%
    // On fixed code: JavaScript = (50000/100000)*100 = 50%
    expect(totalPercentage).toBeCloseTo(100, 0.1);
  });

  /**
   * Bug 2: LeetCode contest note uses wrong CSS class 'ac-no-contest-note'
   * 
   * Expected to FAIL on unfixed code: element may be unstyled or incorrectly styled
   * Counterexample: Element has class 'ac-no-contest-note' which doesn't have proper styling
   */
  it('Bug 2: LeetCode contest note should have appropriate styling', async () => {
    const leetcodeData = {
      username: 'testuser',
      total: 100,
      easy: 40,
      medium: 45,
      hard: 15,
      ranking: 50000
    };

    const { container } = render(<LeetCodeAnalytics data={leetcodeData} />);
    
    // Import act from testing library
    const { act } = await import('@testing-library/react');
    
    // Switch to contest view
    await act(async () => {
      const contestTab = screen.getByText('Contest');
      contestTab.click();
    });
    
    // Find elements with the wrong CSS class
    const wrongClassElements = container.querySelectorAll('.ac-no-contest-note');
    
    // Document the counterexample
    console.log('Bug 2 Counterexample:');
    console.log('  Found elements with wrong class "ac-no-contest-note":', wrongClassElements.length);
    
    if (wrongClassElements.length > 0) {
      wrongClassElements.forEach((el, i) => {
        console.log(`  Element ${i + 1}:`, el.textContent);
        console.log(`  Element ${i + 1} classes:`, el.className);
      });
      console.log('  BUG CONFIRMED: Element uses wrong CSS class "ac-no-contest-note"');
    } else {
      console.log('  BUG NOT FOUND: No elements with class "ac-no-contest-note" (may be already fixed)');
    }
    
    // This assertion will FAIL on unfixed code because the element uses
    // the wrong CSS class 'ac-no-contest-note'
    // On unfixed code: element has class 'ac-no-contest-note'
    // On fixed code: element should have appropriate styling (different class or inline styles)
    expect(wrongClassElements.length).toBe(0);
  });

  /**
   * Bug 3: LeetCode profile link missing icon
   * 
   * Expected behavior: Profile link should contain an icon element before the username
   * Note: Current code appears to already have this icon - verify if bug exists
   */
  it('Bug 3: LeetCode profile link should display an icon', () => {
    const leetcodeData = {
      username: 'testuser',
      total: 100,
      easy: 40,
      medium: 45,
      hard: 15,
      ranking: 50000
    };

    const { container } = render(<LeetCodeAnalytics data={leetcodeData} />);
    
    // Find the profile link
    const profileLink = container.querySelector('a[href*="leetcode.com"]');
    
    // Check if link contains an icon (img or svg element)
    const hasIcon = profileLink?.querySelector('img, svg') !== null;
    
    // Document the counterexample
    console.log('Bug 3 Verification:');
    console.log('  Profile link found:', !!profileLink);
    console.log('  Profile link HTML:', profileLink?.innerHTML);
    console.log('  Has icon element:', hasIcon);
    
    if (!hasIcon) {
      console.log('  BUG CONFIRMED: LeetCode profile link missing icon');
    } else {
      console.log('  BUG NOT FOUND: LeetCode profile link already has icon (may be already fixed)');
    }
    
    // This assertion checks if the icon is present
    // If this PASSES on unfixed code, the bug may already be fixed
    expect(hasIcon).toBe(true);
  });

  /**
   * Bug 4: LinkedIn profile link missing icon
   * 
   * Expected behavior: Profile link should contain an icon element before "View Profile"
   * Note: Current code appears to already have this icon - verify if bug exists
   */
  it('Bug 4: LinkedIn profile link should display an icon', () => {
    const linkedinData = {
      score: 85,
      reasoning: 'Strong profile',
      candidate: {
        full_name: 'Test User',
        current_title: 'Software Engineer',
        company_name: 'Tech Corp',
        location: 'San Francisco',
        years_exp: 5,
        degree_type: 'Bachelor',
        field_of_study: 'Computer Science',
        institution: 'Test University',
        technical_skills: 'JavaScript, Python, React'
      },
      linkedinUrl: 'https://linkedin.com/in/testuser'
    };

    const { container } = render(
      <LinkedInAnalytics 
        score={linkedinData.score}
        reasoning={linkedinData.reasoning}
        candidate={linkedinData.candidate}
        linkedinUrl={linkedinData.linkedinUrl}
      />
    );
    
    // Find the profile link
    const profileLink = container.querySelector('a[href*="linkedin.com"]');
    
    // Check if link contains an icon (img or svg element)
    const hasIcon = profileLink?.querySelector('img, svg') !== null;
    
    // Document the counterexample
    console.log('Bug 4 Verification:');
    console.log('  Profile link found:', !!profileLink);
    console.log('  Profile link HTML:', profileLink?.innerHTML);
    console.log('  Has icon element:', hasIcon);
    
    if (!hasIcon) {
      console.log('  BUG CONFIRMED: LinkedIn profile link missing icon');
    } else {
      console.log('  BUG NOT FOUND: LinkedIn profile link already has icon (may be already fixed)');
    }
    
    // This assertion checks if the icon is present
    // If this PASSES on unfixed code, the bug may already be fixed
    expect(hasIcon).toBe(true);
  });
});
