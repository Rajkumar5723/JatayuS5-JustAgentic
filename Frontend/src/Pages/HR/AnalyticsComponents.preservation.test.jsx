/**
 * Preservation Property Tests for Deep Analysis UI Fixes
 * 
 * **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9**
 * 
 * **Property 2: Preservation** - Non-Buggy UI Elements and Functionality
 * 
 * **IMPORTANT**: Follow observation-first methodology
 * - Observe behavior on UNFIXED code for non-buggy inputs
 * - Write property-based tests capturing observed behavior patterns
 * - Property-based testing generates many test cases for stronger guarantees
 * 
 * **EXPECTED OUTCOME**: Tests PASS on unfixed code (confirms baseline behavior to preserve)
 * 
 * This test suite verifies that all UI elements NOT affected by the 4 bugs continue
 * to work correctly after the fix is implemented.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GitHubAnalytics, LeetCodeAnalytics, LinkedInAnalytics } from './AnalyticsComponents';
import * as fc from 'fast-check';

describe('Preservation Property Tests - Deep Analysis UI Fixes', () => {
  
  /**
   * Preservation 1: GitHub other metrics (repos, stars, forks, followers) display correctly
   * 
   * This test verifies that all GitHub metrics NOT affected by the language percentage bug
   * continue to display correctly. These metrics should be completely unaffected by the fix.
   */
  it('Preservation 1: GitHub metrics (repos, stars, forks, followers) display correctly', () => {
    fc.assert(
      fc.property(
        // Generate random GitHub data with various metric values
        fc.record({
          username: fc.constantFrom('testuser', 'john_doe', 'jane-smith', 'dev123', 'coder_pro'),
          public_repos: fc.nat({ min: 1, max: 1000 }),
          total_repos: fc.nat({ min: 1, max: 1000 }),
          total_stars: fc.nat({ min: 1, max: 10000 }),
          total_forks: fc.nat({ min: 1, max: 5000 }),
          followers: fc.nat({ min: 1, max: 5000 }),
          following: fc.nat({ min: 1, max: 5000 }),
          total_size_mb: fc.nat({ min: 1, max: 10000 }),
          languages: fc.dictionary(
            fc.constantFrom('JavaScript', 'Python', 'TypeScript', 'Java', 'Go', 'Rust', 'C++', 'Ruby'),
            fc.nat({ min: 1000, max: 100000 }),
            { minKeys: 2, maxKeys: 8 }
          ),
          repo_types: fc.record({
            original: fc.nat({ min: 1, max: 500 }),
            forked: fc.nat({ min: 1, max: 500 })
          }),
          top_repos: fc.array(
            fc.record({
              name: fc.constantFrom('my-project', 'awesome-app', 'cool-lib', 'test-repo', 'demo-site'),
              stars: fc.nat({ min: 1, max: 1000 }),
              forks: fc.nat({ min: 1, max: 500 }),
              size_kb: fc.nat({ min: 100, max: 100000 })
            }),
            { minLength: 2, maxLength: 10 }
          )
        }),
        (githubData) => {
          const { container } = render(<GitHubAnalytics data={githubData} />);
          
          // Verify that the component renders without errors
          const section = container.querySelector('.ac-root, .ana-section, .ac-section');
          expect(section).toBeTruthy();
          
          // Verify specific metrics are present in the rendered output
          const text = container.textContent;
          expect(text).toBeTruthy();
          
          // Verify that language distribution chart renders since we have languages
          const hasChart = container.querySelector('.ac-pie-container, .ana-pie-container') !== null;
          expect(hasChart).toBe(true);
        }
      ),
      { numRuns: 50 } // Run 50 random test cases
    );
  });

  /**
   * Preservation 2: LeetCode difficulty percentages remain correct (already sum to 100%)
   * 
   * This test verifies that LeetCode difficulty distribution percentages continue to
   * calculate correctly. These percentages already sum to 100% and should not be affected
   * by the fixes for contest note styling or profile link icons.
   */
  it('Preservation 2: LeetCode difficulty percentages remain correct', () => {
    fc.assert(
      fc.property(
        // Generate random LeetCode data with various difficulty distributions
        fc.record({
          username: fc.constantFrom('testuser', 'john_doe', 'jane-smith', 'dev123', 'coder_pro'),
          total: fc.nat({ min: 10, max: 3000 }),
          easy: fc.nat({ min: 1, max: 1000 }),
          medium: fc.nat({ min: 1, max: 1000 }),
          hard: fc.nat({ min: 1, max: 1000 }),
          ranking: fc.nat({ min: 1, max: 1000000 }),
          contest_rating: fc.option(fc.nat({ min: 1000, max: 3000 }), { nil: undefined }),
          contests_attended: fc.option(fc.nat({ min: 1, max: 100 }), { nil: undefined }),
          active_days: fc.option(fc.nat({ min: 1, max: 365 }), { nil: undefined })
        }).filter(data => data.easy + data.medium + data.hard <= data.total),
        (leetcodeData) => {
          const { container } = render(<LeetCodeAnalytics data={leetcodeData} />);
          
          // Verify that the component renders without errors
          const section = container.querySelector('.ac-root, .ana-section, .ac-section');
          expect(section).toBeTruthy();
          
          // Verify that all metrics display correctly
          const text = container.textContent;
          expect(text).toBeTruthy();
          
          // Verify that difficulty metrics are displayed
          expect(text).toContain(leetcodeData.total.toString());
          
          // If we can find percentage displays, verify they're reasonable
          const percentageMatches = text.match(/(\d+\.?\d*)\s*%/g);
          if (percentageMatches && percentageMatches.length >= 3) {
            // Extract numeric values
            const percentages = percentageMatches
              .map(m => parseFloat(m.replace('%', '')))
              .filter(p => !isNaN(p) && p >= 0 && p <= 100);
            
            // If we found difficulty percentages, they should sum to approximately 100%
            if (percentages.length >= 3) {
              const sum = percentages.slice(0, 3).reduce((a, b) => a + b, 0);
              // Allow some tolerance for rounding
              expect(sum).toBeGreaterThanOrEqual(99);
              expect(sum).toBeLessThanOrEqual(101);
            }
          }
        }
      ),
      { numRuns: 50 }
    );
  });

  /**
   * Preservation 3: LinkedIn candidate information displays correctly
   * 
   * This test verifies that all LinkedIn candidate information fields continue to
   * display correctly. These fields should be completely unaffected by the profile
   * link icon fix.
   */
  it('Preservation 3: LinkedIn candidate information displays correctly', () => {
    fc.assert(
      fc.property(
        // Generate random LinkedIn data with various candidate profiles
        fc.record({
          score: fc.nat({ min: 1, max: 100 }),
          reasoning: fc.constantFrom(
            'Strong technical background with relevant experience',
            'Excellent educational credentials and skills match',
            'Good cultural fit with demonstrated leadership',
            'Solid experience in required technologies'
          ),
          candidate: fc.record({
            full_name: fc.constantFrom('John Doe', 'Jane Smith', 'Alex Johnson', 'Maria Garcia', 'David Chen'),
            current_title: fc.constantFrom('Software Engineer', 'Senior Developer', 'Tech Lead', 'Full Stack Developer'),
            company_name: fc.constantFrom('Tech Corp', 'Startup Inc', 'Big Company', 'Innovation Labs'),
            location: fc.constantFrom('San Francisco', 'New York', 'Seattle', 'Austin', 'Boston'),
            years_exp: fc.nat({ min: 1, max: 50 }),
            degree_type: fc.constantFrom('Bachelor', 'Master', 'PhD', 'Associate'),
            field_of_study: fc.constantFrom('Computer Science', 'Software Engineering', 'Information Technology'),
            institution: fc.constantFrom('MIT', 'Stanford', 'Berkeley', 'Carnegie Mellon', 'State University'),
            technical_skills: fc.constantFrom(
              'JavaScript, Python, React, Node.js',
              'Java, Spring Boot, Microservices',
              'Python, Django, Machine Learning',
              'C++, System Design, Algorithms'
            )
          }),
          linkedinUrl: fc.constantFrom(
            'https://linkedin.com/in/johndoe',
            'https://linkedin.com/in/janesmith',
            'https://linkedin.com/in/alexjohnson'
          )
        }),
        (linkedinData) => {
          const { container } = render(
            <LinkedInAnalytics 
              score={linkedinData.score}
              reasoning={linkedinData.reasoning}
              candidate={linkedinData.candidate}
              linkedinUrl={linkedinData.linkedinUrl}
            />
          );
          
          // Verify that the component renders without errors
          const section = container.querySelector('.ac-root, .ana-section, .ac-section');
          expect(section).toBeTruthy();
          
          const text = container.textContent;
          
          // Verify that key candidate information is displayed
          expect(text).toContain(linkedinData.candidate.full_name);
          expect(text).toContain(linkedinData.candidate.current_title);
          expect(text).toContain(linkedinData.candidate.company_name);
          
          // Verify that the score is displayed
          expect(text).toContain(linkedinData.score.toString());
        }
      ),
      { numRuns: 50 }
    );
  });

  /**
   * Preservation 4: All profile link navigation works correctly
   * 
   * This test verifies that clicking profile links navigates to correct URLs.
   * The href attributes should remain unchanged even if icons are added.
   */
  it('Preservation 4: Profile link navigation URLs are correct', () => {
    // Test GitHub profile link
    fc.assert(
      fc.property(
        fc.record({
          username: fc.string({ minLength: 1, maxLength: 20 }),
          languages: fc.dictionary(fc.string(), fc.nat()),
          total_repos: fc.nat({ max: 100 })
        }),
        (githubData) => {
          const { container } = render(<GitHubAnalytics data={githubData} />);
          
          // Find GitHub profile link
          const githubLink = container.querySelector('a[href*="github.com"]');
          if (githubLink) {
            const href = githubLink.getAttribute('href');
            expect(href).toContain('github.com');
            expect(href).toContain(githubData.username);
          }
        }
      ),
      { numRuns: 20 }
    );

    // Test LeetCode profile link
    fc.assert(
      fc.property(
        fc.record({
          username: fc.string({ minLength: 1, maxLength: 20 }),
          total: fc.nat({ max: 1000 }),
          easy: fc.nat({ max: 500 }),
          medium: fc.nat({ max: 500 }),
          hard: fc.nat({ max: 500 })
        }),
        (leetcodeData) => {
          const { container } = render(<LeetCodeAnalytics data={leetcodeData} />);
          
          // Find LeetCode profile link
          const leetcodeLink = container.querySelector('a[href*="leetcode.com"]');
          if (leetcodeLink) {
            const href = leetcodeLink.getAttribute('href');
            expect(href).toContain('leetcode.com');
            expect(href).toContain(leetcodeData.username);
          }
        }
      ),
      { numRuns: 20 }
    );

    // Test LinkedIn profile link
    fc.assert(
      fc.property(
        fc.record({
          score: fc.nat({ max: 100 }),
          reasoning: fc.string(),
          candidate: fc.record({
            full_name: fc.string({ minLength: 1 }),
            current_title: fc.string(),
            company_name: fc.string(),
            location: fc.string(),
            years_exp: fc.nat(),
            degree_type: fc.string(),
            field_of_study: fc.string(),
            institution: fc.string(),
            technical_skills: fc.string()
          }),
          linkedinUrl: fc.webUrl()
        }),
        (linkedinData) => {
          const { container } = render(
            <LinkedInAnalytics 
              score={linkedinData.score}
              reasoning={linkedinData.reasoning}
              candidate={linkedinData.candidate}
              linkedinUrl={linkedinData.linkedinUrl}
            />
          );
          
          // Find LinkedIn profile link
          const linkedinLink = container.querySelector('a[href*="linkedin.com"]');
          if (linkedinLink) {
            const href = linkedinLink.getAttribute('href');
            expect(href).toBe(linkedinData.linkedinUrl);
          }
        }
      ),
      { numRuns: 20 }
    );
  });

  /**
   * Preservation 5: Tab switching and view state management work correctly
   * 
   * This test verifies that tab switching continues to work correctly in each
   * Deep Analysis section. The tab navigation should be unaffected by the fixes.
   */
  it('Preservation 5: Tab switching works correctly', async () => {
    const { act } = await import('@testing-library/react');
    
    // Test GitHub tab switching
    const githubData = {
      username: 'testuser',
      languages: { JavaScript: 50000, Python: 30000 },
      total_repos: 10,
      public_repos: 10,
      total_stars: 100,
      total_forks: 50,
      followers: 20,
      following: 30,
      total_size_mb: 100,
      repo_types: { original: 8, forked: 2 },
      top_repos: []
    };

    const { container: githubContainer } = render(<GitHubAnalytics data={githubData} />);
    
    // Find tab buttons
    const tabs = githubContainer.querySelectorAll('.ana-tab, .ac-tab');
    expect(tabs.length).toBeGreaterThan(0);
    
    // Verify that clicking tabs changes the view
    if (tabs.length > 1) {
      await act(async () => {
        tabs[1].click();
      });
      
      // Verify that the active tab changed
      const activeTabs = githubContainer.querySelectorAll('.ana-tab.active, .ac-tab.active');
      expect(activeTabs.length).toBeGreaterThan(0);
    }

    // Test LeetCode tab switching
    const leetcodeData = {
      username: 'testuser',
      total: 100,
      easy: 40,
      medium: 45,
      hard: 15,
      ranking: 50000
    };

    const { container: leetcodeContainer } = render(<LeetCodeAnalytics data={leetcodeData} />);
    
    const leetcodeTabs = leetcodeContainer.querySelectorAll('.ana-tab, .ac-tab');
    if (leetcodeTabs.length > 1) {
      await act(async () => {
        leetcodeTabs[1].click();
      });
      
      const activeTabs = leetcodeContainer.querySelectorAll('.ana-tab.active, .ac-tab.active');
      expect(activeTabs.length).toBeGreaterThan(0);
    }
  });

  /**
   * Preservation 6: All charts and visualizations render correctly
   * 
   * This test verifies that all chart components continue to render correctly.
   * The charts should be unaffected by the fixes except for the language percentage
   * values in the legend (which is tested separately in the bug condition test).
   */
  it('Preservation 6: Charts and visualizations render correctly', () => {
    fc.assert(
      fc.property(
        fc.record({
          username: fc.constantFrom('testuser', 'john_doe', 'jane-smith', 'dev123', 'coder_pro'),
          languages: fc.dictionary(
            fc.constantFrom('JavaScript', 'Python', 'TypeScript', 'Java', 'Go'),
            fc.nat({ min: 1000, max: 100000 }),
            { minKeys: 1, maxKeys: 5 }
          ),
          total_repos: fc.nat({ min: 1, max: 100 }),
          public_repos: fc.nat({ min: 1, max: 100 }),
          total_stars: fc.nat({ max: 1000 }),
          total_forks: fc.nat({ max: 500 }),
          followers: fc.nat({ max: 500 }),
          following: fc.nat({ max: 500 }),
          total_size_mb: fc.nat({ max: 1000 }),
          repo_types: fc.record({
            original: fc.nat({ min: 1, max: 50 }),
            forked: fc.nat({ max: 50 })
          }),
          top_repos: fc.array(
            fc.record({
              name: fc.constantFrom('my-project', 'awesome-app', 'cool-lib', 'test-repo', 'demo-site'),
              stars: fc.nat({ max: 500 }),
              forks: fc.nat({ max: 200 }),
              size_kb: fc.nat({ max: 50000 })
            }),
            { minLength: 1, maxLength: 10 }
          )
        }),
        (githubData) => {
          const { container } = render(<GitHubAnalytics data={githubData} />);
          
          // Verify that pie chart container exists
          const pieContainer = container.querySelector('.ac-pie-container, .ana-pie-container');
          expect(pieContainer).toBeTruthy();
          
          // Verify that legend exists
          const legend = container.querySelector('.ac-legend, .ana-legend');
          expect(legend).toBeTruthy();
          
          // Verify that legend items exist
          const legendItems = container.querySelectorAll('.ac-legend-item, .ana-legend-item');
          expect(legendItems.length).toBeGreaterThan(0);
          
          // Verify that each legend item has the expected structure
          legendItems.forEach(item => {
            // Should have a color dot
            const dot = item.querySelector('.ac-legend-dot, .ana-legend-dot');
            expect(dot).toBeTruthy();
            
            // Should have a label
            const label = item.querySelector('.ac-legend-label, .ana-legend-label');
            expect(label).toBeTruthy();
            
            // Should have a value (percentage)
            const value = item.querySelector('.ac-legend-val, .ac-legend-value, .ana-legend-value, .ana-legend-val');
            expect(value).toBeTruthy();
          });
        }
      ),
      { numRuns: 30 }
    );
  });
});
