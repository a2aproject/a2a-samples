# Critic Revision Workflow Test Prompts

Test prompts to verify the critic revision workflow on the `feature/critic-revision-workflow` branch.

---

## Test Prompt 1: Likely to trigger POST revision (weak CTAs, casual tone)

```
Create a complete social media campaign for:

Product: LuxeWatch - Premium Swiss mechanical watches ($5,000-$15,000)
Target Audience: High-net-worth professionals, 40-55 years old, appreciate craftsmanship
Platform: Instagram
Goal: Position as luxury investment pieces, drive boutique appointments
Budget: $10,000
Timeline: 3 weeks until launch
Brand Voice: Sophisticated, authoritative, heritage-focused

Deliverables:
- Market research
- 3 Instagram posts
- Visual concepts
- Quality review with revisions if needed
- Project timeline in Notion

Please create the complete campaign.
```

**Expected behavior**: Copywriter might initially use casual tone which critic will flag as NEEDS_REVISION for luxury audience. Orchestrator should call copywriter again with critic feedback.

---

## Test Prompt 2: Likely to trigger VISUAL revision (generic imagery)

```
Create a complete social media campaign for:

Product: EcoFlow - Smart home energy management system
Target Audience: Tech-savvy homeowners, 35-50, environmentally conscious
Platform: Instagram
Goal: Showcase innovative technology and sustainability benefits
Budget: $7,000
Timeline: 2 weeks until launch
Brand Voice: Innovative, trustworthy, forward-thinking

Deliverables:
- Market research
- 3 Instagram posts highlighting: AI energy optimization, carbon footprint tracking, smart grid integration
- Visual concepts (must show the actual product interface/hardware, not just generic green imagery)
- Quality review with revisions if needed
- Project timeline in Notion

Please create the complete campaign.
```

**Expected behavior**: Designer might create generic eco imagery. Critic should flag as NEEDS_REVISION for not showing actual product. Orchestrator calls designer again.

---

## Test Prompt 3: Likely to get approved (clear, well-defined brief)

```
Create a complete social media campaign for:

Product: BarkBox - Monthly dog treat subscription box
Target Audience: Dog owners, 25-40, treat dogs as family members
Platform: Instagram
Goal: Drive subscriptions through emotional connection and product showcase
Budget: $4,000
Timeline: 2 weeks
Brand Voice: Playful, warm, dog-obsessed (talk TO the dogs, not owners)

Deliverables:
- Market research on pet subscription market
- 3 Instagram posts (use dog POV: "My human got me...", show treats, emphasize monthly surprise)
- Visual concepts (happy dogs enjoying treats, unboxing moment, variety showcase)
- Quality review
- Project timeline in Notion

Please create the complete campaign with strong CTAs and authentic dog-parent voice.
```

**Expected behavior**: Clear brief should result in good initial work. Critic likely approves all. No revisions needed. Proceeds directly to PM.

---

## Test Prompt 4: Likely to trigger BOTH revisions

```
Create a complete social media campaign for:

Product: MindfulMed - Mental health therapy app with AI-powered matching
Target Audience: Young professionals experiencing anxiety/burnout, 25-35
Platform: Instagram
Goal: Build trust, reduce stigma, drive app downloads
Budget: $6,000
Timeline: 3 weeks
Brand Voice: Professional yet empathetic, evidence-based, destigmatizing

CRITICAL REQUIREMENTS:
- Copy must be clinically sensitive (avoid trivializing mental health)
- Visuals must avoid clichés (no sad person staring out window, no head-in-hands)
- Include therapist credentials/app features, not just emotional appeals
- Strong, clear CTAs (not just "feel better")

Deliverables:
- Market research on mental health app market
- 3 Instagram posts
- Visual concepts
- Quality review with revisions if needed
- Project timeline in Notion

Please create the complete campaign.
```

**Expected behavior**: Sensitive topic with strict requirements. Copywriter might be too casual or vague. Designer might use cliché imagery. Critic should flag both as NEEDS_REVISION. Orchestrator calls both agents for revisions.

---

## What to Observe in Test Results

### 1. Revision Workflow Triggers
- Orchestrator announces revision plan: "The Critic identified that the posts need improvement (Score: X/10)..."
- Orchestrator explains what needs revision and why

### 2. Correct Agent Called for Revision
- Posts need revision → calls **copywriter** with critic feedback
- Visuals need revision → calls **designer** with critic feedback
- Both need revision → calls **both** (copywriter first, then designer)

### 3. Revision Context is Complete
Agent receives:
- Original brief
- Their first version
- Critic's exact feedback
- Clear "REVISION" instruction

### 4. Maximum 1 Revision Per Agent
- Even if critic still suggests changes after revision, orchestrator proceeds to PM
- This prevents infinite revision loops and cost explosion

### 5. All 5 Agents Complete
Full workflow:
1. **brand_strategist** → market research
2. **copywriter** → posts
3. **designer** → visual concepts
4. **critic** → quality review
5. **[Revisions if needed]** → copywriter/designer called again with feedback
6. **project_manager** → timeline + Notion entries

### 6. Notion Integration Works
- PM creates project entry in Projects database
- PM creates 5-10 tasks in Tasks database
- Check Notion to verify entries were created

---

## Testing in Agent Engine Playground

1. Go to Agent Engine in Google Cloud Console
2. Select the Creative Director reasoning engine
3. Copy/paste one of the test prompts above
4. Watch for:
   - All 5 agents being called
   - Critic providing structured feedback
   - Revisions being triggered if needed
   - PM creating Notion entries at the end
5. Verify in Notion that project + tasks were created

---

## Expected Revision Workflow Output Example

```
✓ Brand Strategist complete
✓ Copywriter complete (created 3 posts)
✓ Designer complete (created image concepts)
✓ Critic complete

The Critic identified that the posts need improvement (Score: 6/10).
Issue: Tone too casual for luxury audience, CTAs need strengthening
Visuals were approved (8/10).

Let me work with the Copywriter to revise the posts...

🔧 Tool call: copywriter (revision)
✓ Copywriter revision complete

Now proceeding to Project Manager with revised posts and approved visuals...
✓ Project Manager complete

Campaign ready!
```
