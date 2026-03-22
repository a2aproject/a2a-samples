# Orchestrator Test Cases

Test cases for validating the Creative Director orchestrator with both multi-agent workflows and single-agent calls.

---

## Test Case 1: Full Multi-Agent Campaign Creation (5 Agents)

**Objective**: Verify orchestrator can coordinate all 5 specialist agents sequentially to create a complete social media campaign.

**Input Prompt**:
```
Create a complete Instagram campaign for:
- Product: EcoFlow smart water bottle with temperature display
- Target Audience: Fitness enthusiasts and gym-goers, 25-40 years old
- Platform: Instagram
- Goal: Product launch and drive pre-orders
- Budget: $8,000
- Timeline: Launch in 3 weeks
- Brand Voice: Energetic, inspiring, tech-forward

Please create: market research, 3 Instagram posts with captions, visual concepts, quality review, and project timeline.
```

**Expected Behavior**:
1. **Orchestrator announces plan** listing all 5 agents before execution
2. **Brand Strategist** executes → Returns market research (competitors, trends, audience insights)
3. **Orchestrator confirms** → "✓ Research complete. I received..."
4. **Copywriter** executes → Returns 3 Instagram posts with captions and hashtags
5. **Orchestrator confirms** → "✓ Copywriting complete. I received..."
6. **Designer** executes → Returns image generation prompts for each post
7. **Orchestrator confirms** → "✓ Design complete. I received..."
8. **Critic** executes → Returns quality review with ratings and feedback
9. **Orchestrator confirms** → "✓ Review complete. Quality score: ..."
10. **Project Manager** executes → Returns timeline and creates Notion tasks
11. **Orchestrator confirms** → "✓ Project plan complete. Timeline created."
12. **Final presentation** → Orchestrator compiles and presents complete campaign

**Success Criteria**:
- ✅ All 5 agents are called in sequence
- ✅ Orchestrator waits for each response before proceeding
- ✅ Each agent receives context from previous agents
- ✅ No errors or hallucinations ("I'm waiting for..." means failure)
- ✅ Final output contains all sections: Research, Posts, Visuals, Review, Timeline
- ✅ Total execution time: 45-90 seconds

**What to Check**:
```
□ Orchestrator presented plan upfront
□ Brand Strategist returned competitor analysis
□ Brand Strategist returned trending topics
□ Copywriter received strategist insights
□ Copywriter created exactly 3 posts
□ Each post has caption + hashtags
□ Designer received copywriter posts
□ Designer created visual concepts for all 3 posts
□ Critic reviewed all materials (strategy + copy + visuals)
□ Critic provided specific feedback
□ Project Manager created timeline
□ Project Manager created Notion tasks (if configured)
□ All 5 confirmations appeared
□ No "waiting for response" messages
□ Complete campaign presentation at end
```

---

## Test Case 2: Multi-Agent Revision Workflow (Critic Feedback Loop)

**Objective**: Verify orchestrator can handle multi-turn workflows where critic feedback triggers agent revisions.

**Input Prompt (Initial)**:
```
Create a social media campaign for a new vegan protein powder called "PlantFuel":
- Target: Young professionals who work out, 22-35
- Platform: Instagram
- Create 2 posts with visuals
- Include market research and quality review
```

**Expected Behavior (Phase 1 - Initial Creation)**:
1. Orchestrator announces plan (Strategist → Copywriter → Designer → Critic)
2. All 4 agents execute sequentially
3. Critic provides feedback (likely suggests improvements)

**Input Prompt (Follow-up)**:
```
The critic suggested making the tone more energetic. Please update the copy based on this feedback.
```

**Expected Behavior (Phase 2 - Revision)**:
1. Orchestrator identifies this is a revision request
2. **Copywriter** is called again with:
   - Original brief
   - Original posts
   - Critic's feedback about "more energetic tone"
3. Copywriter returns revised posts
4. Orchestrator presents updated posts

**Success Criteria**:
- ✅ Initial workflow completes with all 4 agents
- ✅ Critic provides specific actionable feedback
- ✅ Orchestrator correctly routes revision to Copywriter (not all agents)
- ✅ Copywriter receives feedback context
- ✅ Revised posts reflect critic's suggestions
- ✅ Orchestrator can call same agent multiple times
- ✅ Optional: Critic is called again to verify improvements

**What to Check**:
```
□ Phase 1: All 4 agents executed
□ Phase 1: Critic provided specific feedback
□ Phase 2: Only Copywriter was called (not full workflow)
□ Phase 2: Copywriter acknowledged feedback
□ Phase 2: Revised posts differ from originals
□ Phase 2: Tone is noticeably more energetic
□ No unnecessary agent calls
□ Context preserved across turns
```

---

## Test Case 3: Single Agent Call (Research Only)

**Objective**: Verify orchestrator can correctly identify simple requests and call only one agent without executing full workflow.

**Input Prompt**:
```
Research the eco-friendly water bottle market. Who are the main competitors and what trends are emerging?
```

**Expected Behavior**:
1. **Orchestrator analyzes** request complexity → Simple (research only)
2. **Orchestrator announces** → "I'll call our Brand Strategist for market research"
3. **Brand Strategist** executes → Returns market research
4. **Orchestrator confirms** → "✓ Research complete. Here's what I found..."
5. **Orchestrator presents** → Full research results

**What Should NOT Happen**:
- ❌ Should NOT call Copywriter
- ❌ Should NOT call Designer
- ❌ Should NOT call Critic
- ❌ Should NOT call Project Manager
- ❌ Should NOT create a 5-agent plan

**Success Criteria**:
- ✅ ONLY Brand Strategist is called
- ✅ Request completes in 15-20 seconds (not 60+ seconds)
- ✅ Research covers competitors and trends
- ✅ No error messages or waiting states
- ✅ Orchestrator correctly identified this as simple request

**What to Check**:
```
□ Orchestrator identified request as "research only"
□ Plan mentioned only Brand Strategist (not all 5)
□ Brand Strategist executed
□ Research includes competitor analysis
□ Research includes trending topics
□ NO copywriting was performed
□ NO visual concepts were created
□ NO project timeline was created
□ Execution time < 25 seconds
□ Results presented immediately after strategist
```

**Alternative Simple Request Examples**:
```
✓ "Write 3 Instagram captions for a coffee brand" → Copywriter only
✓ "Create image concepts for a tech startup" → Designer only
✓ "Review these social media posts: [paste content]" → Critic only
✓ "Create a project timeline for launching in 2 weeks" → Project Manager only
```

---

## Testing Checklist Summary

### Full Workflow Test (Test Case 1 & 2)
```bash
# Expected: ~60-90 seconds, all 5 agents called
- [ ] Run Test Case 1: Full campaign creation
- [ ] Verify all 5 agents execute
- [ ] Verify sequential execution with confirmations
- [ ] Run Test Case 2: Revision workflow
- [ ] Verify agent is called multiple times correctly
```

### Single Agent Test (Test Case 3)
```bash
# Expected: ~15-20 seconds, only 1 agent called
- [ ] Run Test Case 3: Research only
- [ ] Verify only Brand Strategist executes
- [ ] Test other single-agent scenarios:
  - [ ] Copy only (Copywriter)
  - [ ] Visuals only (Designer)
  - [ ] Review only (Critic)
```

---

## How to Run Tests

### Option 1: ADK Web UI
```bash
cd agents
adk web
```
- Open browser to http://127.0.0.1:8000
- Select "creative_director" app
- Paste test prompts and observe behavior

### Option 2: Local Python Script
```bash
cd agents/creative_director
python agent.py
```
- Edit the `brief` variable in `__main__` section
- Run and observe terminal output

### Option 3: Deployed Agent Engine
```bash
python deploy/test_deployed_agents.py --test orchestrator
```
- Modify test prompts in the script
- Validates deployed production system

---

## Common Issues & Solutions

### Issue: "Waiting for response..."
**Problem**: Orchestrator says "Waiting for..." but nothing happens
**Cause**: Agent URL not accessible or 403 Forbidden
**Solution**: Check Cloud Run services are deployed and allow unauthenticated

### Issue: Orchestrator stops after 2-3 agents
**Problem**: Workflow doesn't complete all 5 agents
**Cause**: Token limit reached
**Solution**: Verify `max_output_tokens=20000` and compaction config enabled

### Issue: Agent called unnecessarily
**Problem**: All 5 agents called for "research only" request
**Cause**: Orchestrator prompt needs tuning
**Solution**: Review SYSTEM_INSTRUCTION classification examples

### Issue: Agent doesn't receive context
**Problem**: Copywriter doesn't see strategist's research
**Cause**: Context not passed in tool call
**Solution**: Verify orchestrator passes previous outputs explicitly

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Full Workflow Time** | 45-90 seconds | End-to-end execution |
| **Single Agent Time** | 15-25 seconds | Research-only test |
| **Agent Call Accuracy** | 100% | Correct agents for request type |
| **Context Preservation** | 100% | Later agents reference earlier outputs |
| **Error Rate** | 0% | No 403s, timeouts, or hallucinations |
| **Revision Routing** | 100% | Feedback routes to correct agent |

---

## Test Results Template

```markdown
## Test Run: [Date/Time]

### Test Case 1: Full Multi-Agent Campaign
- Status: ✅ Pass / ❌ Fail
- Execution Time: ___ seconds
- Agents Called: [list]
- Issues Found: [description or "None"]

### Test Case 2: Revision Workflow
- Status: ✅ Pass / ❌ Fail
- Agents Called in Phase 1: [list]
- Agents Called in Phase 2: [list]
- Issues Found: [description or "None"]

### Test Case 3: Single Agent Call
- Status: ✅ Pass / ❌ Fail
- Execution Time: ___ seconds
- Agents Called: [should be 1]
- Correct Agent Selected: ✅ Yes / ❌ No
- Issues Found: [description or "None"]

### Overall Assessment
- All Tests Passed: ✅ Yes / ❌ No
- Production Ready: ✅ Yes / ⚠️  Needs Work / ❌ No
- Notes: [additional observations]
```

---

## Next Steps After Testing

1. ✅ All tests pass → Ready for production deployment
2. ⚠️ Partial failures → Review orchestrator prompts and context passing
3. ❌ Major failures → Check agent accessibility and configuration
4. 📊 Performance issues → Verify compaction config and token limits
