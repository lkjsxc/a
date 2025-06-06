/**
 * Action execution engine
 */

import { tool_action, action_result, json_object, json_value } from '../types/common';
import { load_working_memory, save_working_memory, load_storage, save_storage } from './data_manager';
import { load_config } from '../config/config_manager';
import { json_to_xml } from './xml';
import { handle_set_action } from '../tool/set_tool';
import { handle_get_action } from '../tool/get_tool';
import { handle_rm_action } from '../tool/rm_tool';
import { handle_mv_action } from '../tool/mv_tool';
import { handle_ls_action } from '../tool/ls_tool';
import { handle_search_action } from '../tool/search_tool';
import { handle_mkdir_action } from '../tool/mkdir_tool';
import { log_action } from '../tool/action_logger';

// Global action counter for cumulative indexing
let total_action_index = 0;

/**
 * Execute an array of validated tool actions
 */
export async function execute_actions(actions: tool_action[], clearResults: boolean = false): Promise<void> {
  if (actions.length === 0) {
    return;
  }

  // Load current state
  let working_memory = await load_working_memory();
  let storage = await load_storage();

  // Execute each action
  for (const action of actions) {
    total_action_index++;
    const action_index = total_action_index;

    let result: action_result;

    try {
      // Execute the action based on its kind
      switch (action.kind) {
        case 'set':
          result = await handle_set_action(action, working_memory, storage, action_index);
          break;
        case 'get':
          result = await handle_get_action(action, working_memory, storage, action_index);
          break;
        case 'rm':
          result = await handle_rm_action(action, working_memory, storage, action_index);
          break;
        case 'mv':
          result = await handle_mv_action(action, working_memory, storage, action_index);
          break;
        case 'ls':
          result = await handle_ls_action(action, working_memory, storage, action_index);
          break;
        case 'search':
          result = await handle_search_action(action, working_memory, storage, action_index);
          break;
        case 'mkdir':
          result = await handle_mkdir_action(action, working_memory, storage, action_index);
          break;
        default:
          result = {
            action_index,
            timestamp: Date.now(),
            kind: action.kind,
            target_path: action.target_path,
            status: 'error',
            error: `Unknown action kind: ${action.kind}`
          };
      }

      // Add action details to result
      result.kind = action.kind;
      result.target_path = action.target_path;
      if (action.source_path) {
        result.source_path = action.source_path;
      }

    } catch (error) {
      result = {
        action_index,
        timestamp: Date.now(),
        kind: action.kind,
        target_path: action.target_path,
        status: 'error',
        error: `Action execution failed: ${error instanceof Error ? error.message : String(error)}`
      };

      if (action.source_path) {
        result.source_path = action.source_path;
      }
    }    // Store action result in working memory
    try {
      if (!working_memory.action_result) {
        working_memory.action_result = {};
      }
      (working_memory.action_result as json_object)[action_index.toString()] = result;
    } catch (error) {
      console.error('Failed to store action result in working memory:', error);
    }

    // Log the action
    try {
      await log_action(action, result);
    } catch (error) {
      console.error('Failed to log action:', error);
    }

    console.log(`✅ Action ${action_index} (${action.kind}): ${result.status}`);
    if (result.status === 'error') {
      console.error(`   Error: ${result.error}`);
    }
  }
  
  // System statistics processing
  const config = await load_config();
  const working_memory_size = json_to_xml(working_memory, 'working_memory').trim().length;
  const working_memory_size_hard_limit = config.working_memory_character_max || 4096;
  const working_memory_children_max = config.working_memory_children_max || 4;
  // Store system statistics in working memory
  if (!working_memory.system_info) {
    working_memory.system_info = {};
  }
  (working_memory.system_info as json_object).system_stat = {
    working_memory_size,
    working_memory_size_hard_limit,
    working_memory_children_max
  };

  // Save updated state
  await save_working_memory(working_memory);
  await save_storage(storage);
}

/**
 * Clear all action results from working memory
 */
export async function clear_action_results(): Promise<void> {
  const working_memory = await load_working_memory();

  // Clear action_result object
  working_memory.action_result = {};

  await save_working_memory(working_memory);
  console.log('🧹 Cleared all action results from working memory');
}

/**
 * Get the next action index
 */
export function get_next_action_total_index(): number {
  return total_action_index + 1;
}

/**
 * Reset action counter (for testing)
 */
export function reset_action_total_index_counter(): void {
  total_action_index = 0;
}

/**
 * Get current total action index
 */
export function get_current_total_action_index(): number {
  return total_action_index;
}
