"""
Example script to run the VM Snoozing workflow.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from main import VMSnoozingWorkflow
from models.config import WorkflowConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('workflow.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def run_example():
    """Run an example workflow."""
    try:
        # Load configuration from environment
        config = WorkflowConfig.from_env()
        
        logger.info("Starting VM Snoozing workflow example")
        logger.info(f"Target subscription: {config.target_subscription_id}")
        logger.info(f"Schedule: {config.start_time} - {config.stop_time} ({config.timezone})")
        
        # Initialize workflow
        workflow = VMSnoozingWorkflow(config)
        
        # Execute workflow with tag-based VM selection
        result = await workflow.execute(
            subscription_id=config.target_subscription_id,
            vm_selector={
                "tag_selector": {
                    "snooze": "true",
                    "environment": "nonprod"
                }
            }
        )
        
        # Check results
        if result['success']:
            logger.info("✅ Workflow completed successfully!")
            logger.info(f"PR created: {result['pr']['url']}")
            logger.info(f"Branch: {result['branch']}")
            logger.info(f"Files generated: {len(result['files'])}")
            for file_path in result['files']:
                logger.info(f"  - {file_path}")
        else:
            logger.error("❌ Workflow failed!")
            logger.error(f"Error: {result.get('error')}")
            logger.error(f"Details: {result.get('details')}")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_example())
    sys.exit(exit_code)
