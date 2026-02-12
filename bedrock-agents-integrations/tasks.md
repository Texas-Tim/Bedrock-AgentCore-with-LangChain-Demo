# Implementation Plan: Bedrock Agents Integrations

## Overview

This implementation plan adds three Amazon Bedrock Agents features to the AgentCore project: GuardRails for content safety, Knowledge Bases for RAG capabilities, and enhanced Memory integration. The implementation will modify existing agent files in both local and deployed modes, add comprehensive inline documentation, and create a detailed walkthrough guide.

The implementation follows an incremental approach: first adding GuardRails integration, then Knowledge Bases, then enhancing Memory documentation, and finally creating comprehensive documentation and examples that combine all features.

## Tasks

- [ ] 1. Add GuardRails integration to local agents
  - [x] 1.1 Add GuardRails configuration to local/agent.py
    - Add environment variable configuration for BEDROCK_GUARDRAIL_ID and BEDROCK_GUARDRAIL_VERSION
    - Add GuardRails config to ChatBedrock initialization
    - Add inline comments explaining GuardRails parameters
    - Add configuration validation with helpful error messages
    - _Requirements: 3.1, 3.5, 11.1, 11.4_
  
  - [x] 1.2 Add GuardRails error handling to local/agent.py
    - Add try-catch block in stream_response function to handle GuardRails interventions
    - Return user-friendly message when content is blocked
    - Add logging for GuardRails interventions
    - Add inline comments explaining intervention handling
    - _Requirements: 3.2, 12.1_
  
  - [ ]* 1.3 Write unit tests for GuardRails integration in local mode
    - Test GuardRails configuration is passed to ChatBedrock
    - Test agent initializes with and without GuardRails
    - Test intervention handling returns appropriate message
    - Test invalid GuardRail ID raises configuration error
    - _Requirements: 3.1, 3.2, 3.5, 11.4_

- [ ] 2. Add GuardRails integration to deployed agents
  - [x] 2.1 Add GuardRails configuration to deployed/agent.py
    - Add environment variable configuration for GuardRails
    - Add GuardRails config to ChatBedrock initialization
    - Add inline comments explaining GuardRails parameters
    - Add configuration validation
    - _Requirements: 4.1, 11.1, 11.4_
  
  - [x] 2.2 Add GuardRails error handling to deployed/agent.py
    - Add try-catch block in handle_request function for GuardRails interventions
    - Stream user-friendly message when content is blocked
    - Add logging for GuardRails interventions
    - Ensure compatibility with BedrockAgentCoreApp wrapper
    - _Requirements: 4.2, 4.5, 12.1_
  
  - [ ]* 2.3 Write unit tests for GuardRails integration in deployed mode
    - Test GuardRails configuration is passed to ChatBedrock
    - Test BedrockAgentCoreApp compatibility with GuardRails
    - Test intervention handling in streaming context
    - _Requirements: 4.1, 4.2, 4.5_

- [ ] 3. Checkpoint - Ensure GuardRails tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Add Knowledge Base integration to local agents
  - [x] 4.1 Create Knowledge Base tool in local/agent.py
    - Add environment variable configuration for BEDROCK_KNOWLEDGE_BASE_ID
    - Import AmazonKnowledgeBasesRetriever from langchain-aws
    - Create query_knowledge_base tool function with @tool decorator
    - Implement document retrieval and result formatting
    - Add inline comments explaining Knowledge Base query parameters
    - Add tool to agent's tools list
    - _Requirements: 5.1, 5.2, 11.2_
  
  - [x] 4.2 Add Knowledge Base error handling to local/agent.py
    - Add try-catch block in query_knowledge_base tool
    - Handle ResourceNotFoundException with helpful message
    - Handle ValidationException with query format guidance
    - Handle general exceptions gracefully
    - Add logging for Knowledge Base errors
    - Add inline comments explaining error handling
    - _Requirements: 5.5, 12.2_
  
  - [ ]* 4.3 Write unit tests for Knowledge Base integration in local mode
    - Test Knowledge_Base tool is registered in agent's tool list
    - Test tool returns formatted results for valid queries
    - Test tool handles empty results gracefully
    - Test tool handles API errors without crashing
    - Test invalid Knowledge_Base ID raises configuration error
    - _Requirements: 5.1, 5.2, 5.5, 11.4_
  
  - [ ]* 4.4 Write property test for Knowledge Base result formatting
    - **Property 4: Knowledge Base Result Formatting**
    - **Validates: Requirements 5.2, 6.2**

- [ ] 5. Add Knowledge Base integration to deployed agents
  - [x] 5.1 Create Knowledge Base tool in deployed/agent.py
    - Add environment variable configuration for BEDROCK_KNOWLEDGE_BASE_ID
    - Import AmazonKnowledgeBasesRetriever from langchain-aws
    - Create query_knowledge_base tool function
    - Implement document retrieval and result formatting
    - Add inline comments explaining Knowledge Base integration
    - Add tool to agent's tools list
    - Ensure compatibility with BedrockAgentCoreApp streaming
    - _Requirements: 6.1, 6.2, 6.4, 11.2_
  
  - [x] 5.2 Add Knowledge Base error handling to deployed/agent.py
    - Add try-catch block in query_knowledge_base tool
    - Handle various AWS service errors
    - Add logging for Knowledge Base errors
    - Add inline comments explaining error handling
    - _Requirements: 5.5, 12.2_
  
  - [ ]* 5.3 Write unit tests for Knowledge Base integration in deployed mode
    - Test Knowledge_Base tool is registered in agent's tool list
    - Test BedrockAgentCoreApp compatibility with Knowledge_Base tool
    - Test tool calls work correctly in streaming context
    - _Requirements: 6.1, 6.2, 6.4_

- [ ] 6. Checkpoint - Ensure Knowledge Base tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Enhance Memory integration documentation
  - [x] 7.1 Add comprehensive comments to local/agent_with_memory.py
    - Add comments explaining AgentCoreMemorySaver initialization
    - Add comments explaining thread_id and actor_id parameters
    - Add comments explaining memory persistence flow
    - Add comments explaining config structure for memory
    - Add example comments showing different usage patterns
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 8.3_
  
  - [x] 7.2 Add Memory error handling to local/agent_with_memory.py
    - Wrap AgentCoreMemorySaver initialization in try-catch
    - Fall back to stateless agent if memory initialization fails
    - Add logging for memory initialization status
    - Add inline comments explaining fallback behavior
    - _Requirements: 12.3_

- [ ] 8. Create comprehensive example with all features
  - [x] 8.1 Create local/agent_with_all_features.py
    - Combine GuardRails, Knowledge Base, and Memory in single agent
    - Add environment variable configuration for all features
    - Add feature flags to enable/disable each integration
    - Add comprehensive inline comments for all integrations
    - Add validation for all configuration values
    - Add error handling for all features
    - Add logging showing which features are enabled
    - _Requirements: 3.1, 3.2, 3.5, 5.1, 5.2, 5.5, 7.1, 8.1, 8.2, 8.3, 8.4, 11.1, 11.2, 11.3, 11.4, 12.1, 12.2, 12.3, 12.5_
  
  - [x] 8.2 Create deployed/agent_with_all_features.py
    - Combine GuardRails, Knowledge Base, and Memory in single deployed agent
    - Add environment variable configuration for all features
    - Add feature flags to enable/disable each integration
    - Add comprehensive inline comments for all integrations
    - Add validation for all configuration values
    - Add error handling for all features
    - Ensure compatibility with BedrockAgentCoreApp wrapper
    - Add logging showing which features are enabled
    - _Requirements: 4.1, 4.2, 4.5, 6.1, 6.2, 6.4, 7.1, 8.1, 8.2, 8.3, 8.4, 8.5, 11.1, 11.2, 11.3, 11.4, 12.1, 12.2, 12.3, 12.5_
  
  - [ ]* 8.3 Write integration tests for all features combined
    - Test agent with all three features enabled works correctly
    - Test agent handles errors in any feature gracefully
    - Test feature flags enable/disable integrations correctly
    - _Requirements: 12.5_
  
  - [ ]* 8.4 Write property test for feature error resilience
    - **Property 7: Feature Error Resilience**
    - **Validates: Requirements 12.5**

- [ ] 9. Checkpoint - Ensure integration tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Create comprehensive walkthrough documentation
  - [x] 10.1 Create docs/BEDROCK_AGENTS_WALKTHROUGH.md
    - Add introduction explaining all three Bedrock Agents features
    - Add prerequisites section (AWS account, Bedrock access, CLI setup)
    - _Requirements: 9.1_
  
  - [x] 10.2 Add GuardRails setup section to walkthrough
    - Add AWS Console instructions for creating GuardRail
    - Add configuration examples for content filters, denied topics, word filters
    - Add example GuardRail configurations (PII filtering, toxic content blocking)
    - Add instructions for obtaining GuardRail ID and version
    - Add code examples showing GuardRails integration
    - Add example use cases with sample prompts and expected outputs
    - Add troubleshooting guidance for common GuardRails issues
    - Add test prompts for validating GuardRails integration
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 9.2, 9.3, 9.4, 9.5, 10.1, 10.4, 13.1, 13.4_
  
  - [x] 10.3 Add Knowledge Base setup section to walkthrough
    - Add AWS Console instructions for creating Knowledge Base
    - Add configuration examples for data source, embedding model, vector store
    - Add example document formats and data source configurations
    - Add instructions for obtaining Knowledge Base ID
    - Add explanation of indexing process and verification steps
    - Add code examples showing Knowledge Base integration
    - Add example use cases with sample queries and expected outputs
    - Add troubleshooting guidance for common Knowledge Base issues
    - Add test queries for validating Knowledge Base integration
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 9.2, 9.3, 9.4, 9.5, 10.2, 10.4, 13.2, 13.4_
  
  - [x] 10.4 Add Memory setup section to walkthrough
    - Add AWS Console instructions for creating Memory resource
    - Add explanation of thread_id and actor_id parameters
    - Add examples of different Memory usage patterns (single user, multi-user, session management)
    - Add explanation of how Memory state is persisted and retrieved
    - Add Memory limitations and best practices
    - Add code examples showing Memory integration
    - Add example use cases with sample scenarios and expected behaviors
    - Add troubleshooting guidance for common Memory issues
    - Add test scenarios for validating Memory persistence
    - _Requirements: 7.2, 7.3, 7.4, 7.5, 9.2, 9.3, 9.4, 9.5, 10.3, 10.4, 13.3, 13.4_
  
  - [x] 10.5 Add end-to-end example to walkthrough
    - Add complete example using all three features together
    - Add explanation of how features work together
    - Add advanced use cases combining multiple features
    - Add sample prompts demonstrating combined functionality
    - Add expected agent behaviors for combined features
    - Add guidance on verifying integrations in local mode
    - Add guidance on verifying integrations in deployed mode
    - _Requirements: 9.6, 10.5, 13.5_

- [ ] 11. Update existing documentation
  - [x] 11.1 Update local/README.md
    - Add section on GuardRails integration
    - Add section on Knowledge Base integration
    - Add section on Memory integration
    - Add links to comprehensive walkthrough
    - Add configuration instructions
    - _Requirements: 9.1, 11.3_
  
  - [x] 11.2 Update deployed/README.md
    - Add section on GuardRails integration for deployed mode
    - Add section on Knowledge Base integration for deployed mode
    - Add section on Memory integration for deployed mode
    - Add deployment-specific configuration notes
    - Add links to comprehensive walkthrough
    - _Requirements: 9.1, 11.3_
  
  - [x] 11.3 Update main README.md
    - Add overview of Bedrock Agents features
    - Add quick start examples for each feature
    - Add link to comprehensive walkthrough
    - Update project structure to show new files
    - _Requirements: 9.1, 11.3_

- [ ] 12. Add AWS permissions documentation
  - [x] 12.1 Create docs/AWS_PERMISSIONS.md
    - Document required IAM permissions for GuardRails
    - Document required IAM permissions for Knowledge Base
    - Document required IAM permissions for Memory
    - Provide complete IAM policy example
    - Add instructions for setting up IAM roles for deployed mode
    - Add troubleshooting for permission errors
    - _Requirements: 12.4_

- [ ] 13. Final checkpoint - Ensure all documentation is complete
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- All three integrations (GuardRails, Knowledge Base, Memory) are independent and can be enabled/disabled via configuration
- The implementation maintains backward compatibility - existing agents continue to work without modifications
- Comprehensive inline comments and documentation are critical for this feature since many requirements are documentation-focused
